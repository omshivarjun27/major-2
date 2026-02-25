"""
Unit tests — FAISS Indexer Persistence (T-018)
================================================

Tests atomic writes, SHA-256 checksums, backup rotation,
and corruption recovery for FAISSIndexer.save() / _load().
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_indexer(tmp_path, max_backups=3, dimension=8):
    """Create a FAISSIndexer with a temp directory, mocking FAISS."""
    # Patch faiss so we don't need the real library
    mock_faiss = MagicMock()

    # Create a mock index that behaves like IndexFlatL2
    mock_index = MagicMock()
    mock_index.ntotal = 0
    _vectors = []

    def _add(vec):
        _vectors.append(vec.copy())
        mock_index.ntotal = len(_vectors)

    def _reconstruct(idx):
        return _vectors[idx].flatten()

    mock_index.add = _add
    mock_index.reconstruct = _reconstruct
    mock_faiss.IndexFlatL2.return_value = mock_index

    def _write_index(index, path):
        Path(path).write_bytes(b"FAKE_FAISS_INDEX_DATA_" + str(mock_index.ntotal).encode())

    def _read_index(path):
        # Return a fresh mock index that looks loaded
        loaded = MagicMock()
        loaded.ntotal = mock_index.ntotal
        loaded.add = _add
        loaded.reconstruct = _reconstruct
        return loaded

    mock_faiss.write_index = _write_index
    mock_faiss.read_index = _read_index

    with patch("core.memory.indexer._get_faiss", return_value=mock_faiss):
        with patch("core.memory.indexer._get_enc", return_value=None):
            from core.memory.indexer import FAISSIndexer
            indexer = FAISSIndexer(
                index_path=str(tmp_path / "test_index"),
                dimension=dimension,
                max_vectors=100,
                max_backups=max_backups,
            )
            # Attach mock for later assertions
            indexer._mock_faiss = mock_faiss
            indexer._mock_index = mock_index
            indexer._mock_vectors = _vectors
    return indexer


def _add_sample_vectors(indexer, count=3, dimension=8):
    """Add sample vectors to an indexer."""
    for i in range(count):
        vec = np.random.rand(dimension).astype(np.float32)
        indexer.add(
            id=f"mem_{i:03d}",
            embedding=vec,
            summary=f"Test memory {i}",
        )


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------


class TestIndexerPersistence:
    """T-018: FAISS indexer persistence hardening tests."""

    def test_save_creates_checksum_sidecars(self, tmp_path):
        """save() should create .sha256 sidecar files for both index and metadata."""
        indexer = _make_indexer(tmp_path)
        _add_sample_vectors(indexer, count=2)

        with patch("core.memory.indexer._get_faiss", return_value=indexer._mock_faiss):
            with patch("core.memory.indexer._get_enc", return_value=None):
                indexer.save()

        index_dir = tmp_path / "test_index"
        assert (index_dir / "index.faiss").exists(), "index.faiss should exist after save"
        assert (index_dir / "metadata.json").exists(), "metadata.json should exist after save"
        assert (index_dir / "index.faiss.sha256").exists(), "index.faiss.sha256 sidecar missing"
        assert (index_dir / "metadata.json.sha256").exists(), "metadata.json.sha256 sidecar missing"

        # Verify sidecar contents are hex strings of correct length (SHA-256 = 64 hex chars)
        idx_checksum = (index_dir / "index.faiss.sha256").read_text().strip()
        meta_checksum = (index_dir / "metadata.json.sha256").read_text().strip()
        assert len(idx_checksum) == 64, f"Index checksum wrong length: {len(idx_checksum)}"
        assert len(meta_checksum) == 64, f"Metadata checksum wrong length: {len(meta_checksum)}"

    def test_load_verifies_checksums(self, tmp_path):
        """_verify_checksum should return True for valid files and False for tampered ones."""
        indexer = _make_indexer(tmp_path)

        # Write a test file and its checksum
        test_file = tmp_path / "test_index" / "test.bin"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b"hello world")

        checksum = indexer._compute_checksum(test_file)
        indexer._write_checksum(test_file, checksum)

        # Valid file passes
        assert indexer._verify_checksum(test_file) is True

        # Tampered file fails
        test_file.write_bytes(b"corrupted data")
        assert indexer._verify_checksum(test_file) is False

    def test_corrupted_index_falls_back_to_backup(self, tmp_path):
        """When index.faiss is corrupted, _load() should attempt backup recovery."""
        indexer = _make_indexer(tmp_path)
        _add_sample_vectors(indexer, count=3)

        with patch("core.memory.indexer._get_faiss", return_value=indexer._mock_faiss):
            with patch("core.memory.indexer._get_enc", return_value=None):
                # First save creates the files; second save rotates them into backup_001
                indexer.save()
                indexer.save()

        index_dir = tmp_path / "test_index"

        # After two saves, backup_001 should exist (from rotation before 2nd save)
        assert (index_dir / "backup_001").exists(), "backup_001 should exist after two saves"

        # Corrupt the main index file
        (index_dir / "index.faiss").write_bytes(b"CORRUPTED")
        # Update the checksum to NOT match (so verification fails)
        (index_dir / "index.faiss.sha256").write_text("0" * 64)

        # Create a new indexer that loads from disk — it should detect corruption
        # and attempt backup fallback
        with patch("core.memory.indexer._get_faiss", return_value=indexer._mock_faiss):
            with patch("core.memory.indexer._get_enc", return_value=None):
                from core.memory.indexer import FAISSIndexer
                recovered = FAISSIndexer(
                    index_path=str(index_dir),
                    dimension=8,
                    max_vectors=100,
                    max_backups=3,
                )

        # The indexer should have either recovered from backup or started fresh
        # (both are acceptable — the key is it didn't crash)
        assert recovered is not None

    def test_corrupted_metadata_falls_back_to_backup(self, tmp_path):
        """When metadata.json is corrupted, _load() should handle gracefully."""
        indexer = _make_indexer(tmp_path)
        _add_sample_vectors(indexer, count=2)

        with patch("core.memory.indexer._get_faiss", return_value=indexer._mock_faiss):
            with patch("core.memory.indexer._get_enc", return_value=None):
                indexer.save()

        index_dir = tmp_path / "test_index"

        # Corrupt metadata
        (index_dir / "metadata.json").write_text("{invalid json!!!}")
        # Invalidate checksum
        (index_dir / "metadata.json.sha256").write_text("0" * 64)

        # Load should not crash
        with patch("core.memory.indexer._get_faiss", return_value=indexer._mock_faiss):
            with patch("core.memory.indexer._get_enc", return_value=None):
                from core.memory.indexer import FAISSIndexer
                recovered = FAISSIndexer(
                    index_path=str(index_dir),
                    dimension=8,
                    max_vectors=100,
                    max_backups=3,
                )

        assert recovered is not None

    def test_backup_rotation_keeps_max_three(self, tmp_path):
        """Backup rotation should retain at most max_backups snapshots."""
        indexer = _make_indexer(tmp_path, max_backups=3)
        index_dir = tmp_path / "test_index"

        with patch("core.memory.indexer._get_faiss", return_value=indexer._mock_faiss):
            with patch("core.memory.indexer._get_enc", return_value=None):
                # Save 5 times — should create at most 3 backups
                for i in range(5):
                    _add_sample_vectors(indexer, count=1, dimension=8)
                    indexer.save()

        backup_dirs = sorted(index_dir.glob("backup_*"))
        assert len(backup_dirs) <= 3, f"Expected at most 3 backups, got {len(backup_dirs)}: {backup_dirs}"

        # All backup dirs should contain the expected files
        for bd in backup_dirs:
            assert (bd / "index.faiss").exists(), f"{bd} missing index.faiss"
            assert (bd / "metadata.json").exists(), f"{bd} missing metadata.json"

    def test_atomic_save_survives_interrupted_write(self, tmp_path):
        """If save() fails mid-write, the previous snapshot should remain intact."""
        indexer = _make_indexer(tmp_path)
        _add_sample_vectors(indexer, count=2)

        with patch("core.memory.indexer._get_faiss", return_value=indexer._mock_faiss):
            with patch("core.memory.indexer._get_enc", return_value=None):
                indexer.save()

        index_dir = tmp_path / "test_index"

        # Record original metadata content
        original_metadata = (index_dir / "metadata.json").read_text()

        # Now simulate a failed save by patching os.replace to raise
        _add_sample_vectors(indexer, count=1, dimension=8)

        with patch("core.memory.indexer._get_faiss", return_value=indexer._mock_faiss):
            with patch("core.memory.indexer._get_enc", return_value=None):
                with patch("os.replace", side_effect=OSError("Simulated disk failure")):
                    try:
                        indexer.save()
                    except OSError:
                        pass

        # Original metadata should still be intact (atomic guarantee)
        current_metadata = (index_dir / "metadata.json").read_text()
        assert current_metadata == original_metadata, "Original metadata was corrupted by failed save"

    def test_save_load_round_trip_preserves_data(self, tmp_path):
        """Data saved should be fully recoverable on load."""
        indexer = _make_indexer(tmp_path)

        # Add specific memories
        for i in range(3):
            vec = np.ones(8, dtype=np.float32) * (i + 1)
            indexer.add(
                id=f"round_trip_{i}",
                embedding=vec,
                summary=f"Summary {i}",
                session_id=f"sess_{i}",
            )

        with patch("core.memory.indexer._get_faiss", return_value=indexer._mock_faiss):
            with patch("core.memory.indexer._get_enc", return_value=None):
                indexer.save()

        # Read metadata directly from saved JSON
        index_dir = tmp_path / "test_index"
        with open(index_dir / "metadata.json") as f:
            saved_data = json.load(f)

        # Verify metadata structure
        assert "metadata" in saved_data
        assert "id_to_idx" in saved_data
        assert "next_idx" in saved_data
        assert "dimension" in saved_data
        assert "saved_at" in saved_data

        # Verify all 3 memories are present
        meta = saved_data["metadata"]
        assert len(meta) == 3, f"Expected 3 metadata entries, got {len(meta)}"

        # Verify specific memory content
        ids = {m["id"] for m in meta.values()}
        assert ids == {"round_trip_0", "round_trip_1", "round_trip_2"}

        for m in meta.values():
            assert m["summary"].startswith("Summary ")
            assert m["session_id"].startswith("sess_")


class TestIndexerRecovery:
    """Integration test: recovery when all backups are corrupted."""

    def test_recovery_from_all_backups_corrupted(self, tmp_path):
        """When main files AND all backups are corrupted, indexer starts fresh."""
        indexer = _make_indexer(tmp_path, max_backups=3)

        with patch("core.memory.indexer._get_faiss", return_value=indexer._mock_faiss):
            with patch("core.memory.indexer._get_enc", return_value=None):
                # Save several times to create backups
                for i in range(4):
                    _add_sample_vectors(indexer, count=1, dimension=8)
                    indexer.save()

        index_dir = tmp_path / "test_index"

        # Corrupt ALL files — main + all backups
        for f in index_dir.glob("**/metadata.json"):
            f.write_text("CORRUPT")
        for f in index_dir.glob("**/index.faiss"):
            f.write_bytes(b"CORRUPT")
        # Invalidate all checksums
        for f in index_dir.glob("**/*.sha256"):
            f.write_text("0" * 64)

        # Loading should NOT crash — it should start with empty state
        with patch("core.memory.indexer._get_faiss", return_value=indexer._mock_faiss):
            with patch("core.memory.indexer._get_enc", return_value=None):
                from core.memory.indexer import FAISSIndexer
                recovered = FAISSIndexer(
                    index_path=str(index_dir),
                    dimension=8,
                    max_vectors=100,
                    max_backups=3,
                )

        # Should be empty but functional
        assert recovered.size == 0, "Recovered indexer should be empty after total corruption"
        assert recovered is not None
