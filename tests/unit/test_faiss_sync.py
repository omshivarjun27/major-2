"""
Unit tests for FAISS Sync Module (T-112).

Tests:
- Storage backends (Local, S3, Azure)
- Merge strategies (Union, LastWriterWins)
- FAISSSyncManager operations
- Checksum verification
- Incremental sync
"""

from unittest.mock import MagicMock

import numpy as np
import pytest

from core.memory.cloud_sync import ChangeLog, UserPartition, VectorTimestamp
from core.memory.faiss_sync import (
    AzureBlobStorageBackend,
    FAISSIndexState,
    FAISSSyncConfig,
    FAISSSyncManager,
    LastWriterWinsMergeStrategy,
    LocalStorageBackend,
    S3StorageBackend,
    UnionMergeStrategy,
    create_faiss_sync_manager,
)


class TestLocalStorageBackend:
    """Tests for LocalStorageBackend."""

    @pytest.fixture
    def storage(self, tmp_path):
        return LocalStorageBackend(base_path=str(tmp_path / "storage"))

    async def test_upload_and_download(self, storage):
        """Test uploading and downloading data."""
        data = b"test data content"
        uploaded = await storage.upload("test/key.bin", data)
        assert uploaded is True

        downloaded = await storage.download("test/key.bin")
        assert downloaded == data

    async def test_upload_with_metadata(self, storage):
        """Test uploading with metadata."""
        data = b"content"
        metadata = {"version": "1.0", "checksum": "abc123"}

        await storage.upload("test/key.bin", data, metadata=metadata)

        retrieved_meta = await storage.get_metadata("test/key.bin")
        assert retrieved_meta == metadata

    async def test_delete(self, storage):
        """Test deleting data."""
        await storage.upload("test/key.bin", b"data")
        assert await storage.exists("test/key.bin")

        deleted = await storage.delete("test/key.bin")
        assert deleted is True
        assert not await storage.exists("test/key.bin")

    async def test_delete_nonexistent(self, storage):
        """Test deleting nonexistent key."""
        deleted = await storage.delete("nonexistent/key.bin")
        assert deleted is False

    async def test_exists(self, storage):
        """Test checking if key exists."""
        assert not await storage.exists("test/key.bin")

        await storage.upload("test/key.bin", b"data")
        assert await storage.exists("test/key.bin")

    async def test_list_keys(self, storage):
        """Test listing keys with prefix."""
        await storage.upload("prefix/a.bin", b"a")
        await storage.upload("prefix/b.bin", b"b")
        await storage.upload("other/c.bin", b"c")

        keys = await storage.list_keys("prefix")
        assert len(keys) == 2
        assert any("a.bin" in k for k in keys)
        assert any("b.bin" in k for k in keys)

    async def test_download_nonexistent(self, storage):
        """Test downloading nonexistent key."""
        result = await storage.download("nonexistent.bin")
        assert result is None


class TestUnionMergeStrategy:
    """Tests for UnionMergeStrategy."""

    @pytest.fixture
    def strategy(self):
        return UnionMergeStrategy()

    def test_merge_disjoint_sets(self, strategy):
        """Test merging disjoint vector sets."""
        local = {"a": np.array([1.0, 2.0]), "b": np.array([3.0, 4.0])}
        remote = {"c": np.array([5.0, 6.0]), "d": np.array([7.0, 8.0])}

        merged, conflicts = strategy.merge(local, remote, {}, {})

        assert len(merged) == 4
        assert "a" in merged
        assert "c" in merged
        assert len(conflicts) == 0

    def test_merge_with_overlap_remote_newer(self, strategy):
        """Test merging with overlap where remote is newer."""
        local = {"a": np.array([1.0, 2.0])}
        remote = {"a": np.array([10.0, 20.0])}

        local_ts = {"a": VectorTimestamp(node_id="node1", clock={"node1": 1})}
        remote_ts = {"a": VectorTimestamp(node_id="node2", clock={"node1": 2})}

        merged, conflicts = strategy.merge(local, remote, local_ts, remote_ts)

        assert len(merged) == 1
        np.testing.assert_array_equal(merged["a"], np.array([10.0, 20.0]))
        assert len(conflicts) == 0

    def test_merge_with_conflict(self, strategy):
        """Test merging with concurrent timestamps (conflict)."""
        local = {"a": np.array([1.0, 2.0])}
        remote = {"a": np.array([10.0, 20.0])}

        # Concurrent: node1 has higher clock for node1, node2 has higher for node2
        local_ts = {"a": VectorTimestamp(node_id="node1", clock={"node1": 2, "node2": 1})}
        remote_ts = {"a": VectorTimestamp(node_id="node2", clock={"node1": 1, "node2": 2})}

        merged, conflicts = strategy.merge(local, remote, local_ts, remote_ts)

        assert "a" in conflicts  # Detected as conflict
        assert "a" in merged  # But still merged (local wins)


class TestLastWriterWinsMergeStrategy:
    """Tests for LastWriterWinsMergeStrategy."""

    @pytest.fixture
    def strategy(self):
        return LastWriterWinsMergeStrategy()

    def test_local_wins_when_newer(self, strategy):
        """Test local wins when it has newer timestamp."""
        local = {"a": np.array([1.0])}
        remote = {"a": np.array([2.0])}

        local_ts = {"a": VectorTimestamp(node_id="node1", clock={"node1": 5})}
        remote_ts = {"a": VectorTimestamp(node_id="node2", clock={"node1": 3})}

        merged, conflicts = strategy.merge(local, remote, local_ts, remote_ts)

        np.testing.assert_array_equal(merged["a"], np.array([1.0]))

    def test_remote_wins_when_newer(self, strategy):
        """Test remote wins when it has newer timestamp."""
        local = {"a": np.array([1.0])}
        remote = {"a": np.array([2.0])}

        local_ts = {"a": VectorTimestamp(node_id="node1", clock={"node1": 3})}
        remote_ts = {"a": VectorTimestamp(node_id="node2", clock={"node1": 5})}

        merged, conflicts = strategy.merge(local, remote, local_ts, remote_ts)

        np.testing.assert_array_equal(merged["a"], np.array([2.0]))

    def test_keeps_unique_vectors(self, strategy):
        """Test both unique vectors are kept."""
        local = {"a": np.array([1.0])}
        remote = {"b": np.array([2.0])}

        merged, conflicts = strategy.merge(local, remote, {}, {})

        assert "a" in merged
        assert "b" in merged
        assert len(conflicts) == 0


class TestFAISSIndexState:
    """Tests for FAISSIndexState dataclass."""

    def test_to_dict(self):
        """Test serialization."""
        state = FAISSIndexState(
            index_id="idx_123",
            partition_id="part_456",
            vector_count=100,
            dimension=384,
            checksum="abc123",
            last_modified_ms=1000.0,
            vector_ids={"v1", "v2"},
            timestamps={"v1": {"node_id": "n1", "clock": {"n1": 1}}},
        )

        data = state.to_dict()

        assert data["index_id"] == "idx_123"
        assert data["vector_count"] == 100
        assert "v1" in data["vector_ids"]

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "index_id": "idx_123",
            "partition_id": "part_456",
            "vector_count": 100,
            "dimension": 384,
            "checksum": "abc123",
            "last_modified_ms": 1000.0,
            "vector_ids": ["v1", "v2"],
            "timestamps": {},
        }

        state = FAISSIndexState.from_dict(data)

        assert state.index_id == "idx_123"
        assert state.vector_count == 100
        assert "v1" in state.vector_ids


class TestFAISSSyncManager:
    """Tests for FAISSSyncManager."""

    @pytest.fixture
    def change_log(self):
        return ChangeLog(node_id="test_node")

    @pytest.fixture
    def partition(self):
        return UserPartition(user_id="test_user")

    @pytest.fixture
    def sync_manager(self, change_log, partition, tmp_path):
        config = FAISSSyncConfig(
            storage_backend="local",
            bucket_or_container=str(tmp_path / "faiss"),
        )
        return FAISSSyncManager(config=config, change_log=change_log, partition=partition)

    async def test_track_add(self, sync_manager):
        """Test tracking vector addition."""
        embedding = np.random.rand(384).astype(np.float32)
        timestamp = VectorTimestamp(node_id="test_node")
        timestamp.increment()

        await sync_manager.track_add("vec_001", embedding, timestamp)

        assert sync_manager.local_vector_count == 1
        assert "vec_001" in sync_manager._local_vectors

    async def test_track_delete(self, sync_manager):
        """Test tracking vector deletion."""
        embedding = np.random.rand(384).astype(np.float32)
        timestamp = VectorTimestamp(node_id="test_node")

        await sync_manager.track_add("vec_001", embedding, timestamp)
        await sync_manager.track_delete("vec_001")

        assert sync_manager.local_vector_count == 0
        assert "vec_001" in sync_manager._deleted_ids

    async def test_push(self, sync_manager):
        """Test pushing vectors to storage."""
        embedding = np.random.rand(384).astype(np.float32)
        timestamp = VectorTimestamp(node_id="test_node")
        timestamp.increment()

        await sync_manager.track_add("vec_001", embedding, timestamp)

        result = await sync_manager.push()

        assert result.success is True
        assert result.pushed_count == 1

    async def test_push_empty(self, sync_manager):
        """Test pushing with no vectors."""
        result = await sync_manager.push()

        assert result.success is True
        assert result.pushed_count == 0

    async def test_pull_empty_storage(self, sync_manager):
        """Test pulling from empty storage."""
        result = await sync_manager.pull()

        assert result.success is True
        assert result.pulled_count == 0

    async def test_push_then_pull(self, sync_manager, partition, change_log, tmp_path):
        """Test round-trip push and pull."""
        # Push some vectors
        embedding = np.random.rand(384).astype(np.float32)
        timestamp = VectorTimestamp(node_id="test_node")
        timestamp.increment()

        await sync_manager.track_add("vec_001", embedding, timestamp)
        await sync_manager.push()

        # Create new manager (simulating different device)
        config = FAISSSyncConfig(
            storage_backend="local",
            bucket_or_container=str(tmp_path / "faiss"),
        )
        new_manager = FAISSSyncManager(config=config, change_log=change_log, partition=partition)

        # Pull
        result = await new_manager.pull()

        assert result.success is True
        assert result.pulled_count == 1
        assert "vec_001" in new_manager._local_vectors

    async def test_checksum_verification(self, sync_manager):
        """Test checksum verification works."""
        embedding = np.random.rand(384).astype(np.float32)
        timestamp = VectorTimestamp(node_id="test_node")

        await sync_manager.track_add("vec_001", embedding, timestamp)
        await sync_manager.push()

        # Corrupt the data
        vectors_key = sync_manager._vectors_key()
        await sync_manager._storage.upload(vectors_key, b"corrupted data")

        # Pull should fail checksum
        result = await sync_manager.pull()

        # Either fails checksum or fails to parse
        assert not result.success or result.error is not None

    async def test_sync_bidirectional(self, sync_manager):
        """Test bidirectional sync."""
        embedding = np.random.rand(384).astype(np.float32)
        timestamp = VectorTimestamp(node_id="test_node")
        timestamp.increment()

        await sync_manager.track_add("vec_001", embedding, timestamp)

        result = await sync_manager.sync()

        assert result.success is True
        assert result.pushed_count == 1

    async def test_health(self, sync_manager):
        """Test health status."""
        health = sync_manager.health()

        assert "partition_id" in health
        assert "local_vector_count" in health
        assert health["storage_backend"] == "local"

    async def test_serialize_deserialize_vectors(self, sync_manager):
        """Test vector serialization round-trip."""
        vectors = {
            "a": np.array([1.0, 2.0, 3.0], dtype=np.float32),
            "b": np.array([4.0, 5.0, 6.0], dtype=np.float32),
        }

        serialized = sync_manager._serialize_vectors(vectors)
        deserialized = sync_manager._deserialize_vectors(serialized)

        assert len(deserialized) == 2
        np.testing.assert_array_almost_equal(deserialized["a"], vectors["a"])
        np.testing.assert_array_almost_equal(deserialized["b"], vectors["b"])


class TestFAISSSyncManagerMerging:
    """Tests for merge scenarios."""

    @pytest.fixture
    def tmp_storage(self, tmp_path):
        return str(tmp_path / "faiss_merge")

    async def test_merge_concurrent_changes(self, tmp_storage):
        """Test merging concurrent changes from two devices."""
        change_log1 = ChangeLog(node_id="device1")
        change_log2 = ChangeLog(node_id="device2")
        partition = UserPartition(user_id="test_user")

        config = FAISSSyncConfig(
            storage_backend="local",
            bucket_or_container=tmp_storage,
        )

        manager1 = FAISSSyncManager(config=config, change_log=change_log1, partition=partition)
        manager2 = FAISSSyncManager(config=config, change_log=change_log2, partition=partition)

        # Device 1 adds vector A
        ts1 = VectorTimestamp(node_id="device1")
        ts1.increment()
        await manager1.track_add("vec_a", np.array([1.0, 2.0], dtype=np.float32), ts1)
        await manager1.push()

        # Device 2 adds vector B (without pulling first - simulates concurrent)
        ts2 = VectorTimestamp(node_id="device2")
        ts2.increment()
        await manager2.track_add("vec_b", np.array([3.0, 4.0], dtype=np.float32), ts2)

        # Device 2 syncs
        result = await manager2.sync()

        assert result.success is True
        # After merge, device 2 should have both vectors
        assert manager2.local_vector_count == 2


class TestCreateFaissSyncManager:
    """Tests for factory function."""

    def test_create_with_defaults(self):
        """Test factory with default parameters."""
        partition = UserPartition(user_id="test_user")
        change_log = ChangeLog(node_id="test_node")

        manager = create_faiss_sync_manager(partition, change_log)

        assert manager.config.storage_backend == "local"
        assert manager.partition == partition

    def test_create_with_s3(self):
        """Test factory with S3 backend."""
        partition = UserPartition(user_id="test_user")
        change_log = ChangeLog(node_id="test_node")

        manager = create_faiss_sync_manager(
            partition,
            change_log,
            storage_backend="s3",
            bucket_or_container="my-bucket",
        )

        assert manager.config.storage_backend == "s3"
        assert manager.config.bucket_or_container == "my-bucket"


class TestS3StorageBackend:
    """Tests for S3 storage backend (mocked)."""

    def test_init(self):
        """Test initialization."""
        backend = S3StorageBackend(
            bucket="test-bucket",
            region="eu-west-1",
        )

        assert backend.bucket == "test-bucket"
        assert backend.region == "eu-west-1"

    async def test_upload_with_mock(self):
        """Test upload with mocked boto3."""
        backend = S3StorageBackend(bucket="test-bucket")

        mock_client = MagicMock()
        backend._client = mock_client

        result = await backend.upload("key", b"data", metadata={"k": "v"})

        mock_client.put_object.assert_called_once()
        assert result is True

    async def test_download_with_mock(self):
        """Test download with mocked boto3."""
        backend = S3StorageBackend(bucket="test-bucket")

        mock_client = MagicMock()
        mock_response = {"Body": MagicMock(read=MagicMock(return_value=b"data"))}
        mock_client.get_object.return_value = mock_response
        backend._client = mock_client

        result = await backend.download("key")

        assert result == b"data"


class TestAzureBlobStorageBackend:
    """Tests for Azure Blob storage backend (mocked)."""

    def test_init(self):
        """Test initialization."""
        backend = AzureBlobStorageBackend(
            container="test-container",
            connection_string="DefaultEndpointsProtocol=https;...",
        )

        assert backend.container == "test-container"


class TestFAISSSyncConfig:
    """Tests for FAISSSyncConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = FAISSSyncConfig()

        assert config.storage_backend == "local"
        assert config.merge_strategy == "union"
        assert config.verify_checksum is True
        assert config.compression is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = FAISSSyncConfig(
            storage_backend="s3",
            bucket_or_container="my-bucket",
            merge_strategy="last_writer_wins",
            verify_checksum=False,
        )

        assert config.storage_backend == "s3"
        assert config.merge_strategy == "last_writer_wins"
        assert config.verify_checksum is False
