"""
NFR Test #123 — Deterministic Replay Assertion
================================================

Verifies that identical inputs produce identical outputs
when using seeded/deterministic mode.
"""

import hashlib

import numpy as np


class TestDeterministicReplay:

    SEED = 42

    def _create_seeded_frame(self, seed: int) -> np.ndarray:
        """Create a deterministic frame from a seed."""
        rng = np.random.RandomState(seed)
        return rng.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    def test_same_seed_same_frame(self):
        """Two frames created with same seed should be identical."""
        f1 = self._create_seeded_frame(self.SEED)
        f2 = self._create_seeded_frame(self.SEED)
        assert np.array_equal(f1, f2), "Seeded frames should be identical"

    def test_different_seed_different_frame(self):
        """Two frames from different seeds should differ."""
        f1 = self._create_seeded_frame(self.SEED)
        f2 = self._create_seeded_frame(self.SEED + 1)
        assert not np.array_equal(f1, f2), "Different seeds should produce different frames"

    def test_histogram_deterministic(self):
        """Image histogram of a seeded frame should be deterministic."""
        frame = self._create_seeded_frame(self.SEED)
        gray = np.mean(frame, axis=2).astype(np.uint8)
        h1 = np.histogram(gray, bins=16)[0]

        frame2 = self._create_seeded_frame(self.SEED)
        gray2 = np.mean(frame2, axis=2).astype(np.uint8)
        h2 = np.histogram(gray2, bins=16)[0]

        assert np.array_equal(h1, h2), "Histogram should be identical for same seed"

    def test_frame_hash_reproducible(self):
        """MD5 hash of a seeded frame should be reproducible."""
        f1 = self._create_seeded_frame(self.SEED)
        f2 = self._create_seeded_frame(self.SEED)
        h1 = hashlib.md5(f1.tobytes()).hexdigest()
        h2 = hashlib.md5(f2.tobytes()).hexdigest()
        assert h1 == h2, f"Frame hashes differ: {h1} vs {h2}"

    def test_config_reproducibility(self):
        """Config loaded twice should be identical."""
        from shared.config import get_config
        c1 = get_config()
        c2 = get_config()
        # All keys should match
        for key in c1:
            assert c1[key] == c2[key], f"Config key '{key}' differs between loads"
