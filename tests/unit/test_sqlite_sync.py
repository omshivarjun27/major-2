"""
Unit tests for SQLite Sync Module (T-113).

Tests:
- CRDT types (LWWRegister, GSet, TwoPhaseSet)
- WAL change tracking
- SQLiteSyncManager operations
- Schema versioning
- Conflict resolution
"""

import sqlite3

import pytest

from core.memory.cloud_sync import UserPartition
from core.memory.sqlite_sync import (
    GSet,
    LWWRegister,
    SchemaVersion,
    SQLiteSyncConfig,
    SQLiteSyncManager,
    TableSyncState,
    TwoPhaseSet,
    WALChange,
    WALChangeTracker,
    create_sqlite_sync_manager,
)


class TestLWWRegister:
    """Tests for Last-Writer-Wins Register."""

    def test_create_register(self):
        """Test creating a register."""
        reg = LWWRegister(value="hello", timestamp_ms=1000.0, node_id="node1")
        assert reg.value == "hello"
        assert reg.timestamp_ms == 1000.0

    def test_merge_newer_wins(self):
        """Test that newer timestamp wins."""
        reg1 = LWWRegister(value="old", timestamp_ms=1000.0, node_id="node1")
        reg2 = LWWRegister(value="new", timestamp_ms=2000.0, node_id="node2")

        result = reg1.merge(reg2)

        assert result.value == "new"
        assert result.timestamp_ms == 2000.0

    def test_merge_older_loses(self):
        """Test that older timestamp loses."""
        reg1 = LWWRegister(value="new", timestamp_ms=2000.0, node_id="node1")
        reg2 = LWWRegister(value="old", timestamp_ms=1000.0, node_id="node2")

        result = reg1.merge(reg2)

        assert result.value == "new"

    def test_merge_tie_breaker(self):
        """Test tie-breaker with equal timestamps."""
        reg1 = LWWRegister(value="a", timestamp_ms=1000.0, node_id="node1")
        reg2 = LWWRegister(value="b", timestamp_ms=1000.0, node_id="node2")

        result = reg1.merge(reg2)

        # node2 > node1 lexicographically, so reg2 wins
        assert result.value == "b"

    def test_to_dict_and_from_dict(self):
        """Test serialization."""
        reg = LWWRegister(value={"key": "value"}, timestamp_ms=1000.0, node_id="node1")
        data = reg.to_dict()

        restored = LWWRegister.from_dict(data)
        assert restored.value == {"key": "value"}
        assert restored.timestamp_ms == 1000.0


class TestGSet:
    """Tests for Grow-only Set."""

    def test_add_items(self):
        """Test adding items."""
        gset = GSet()
        gset.add("a")
        gset.add("b")
        gset.add("a")  # Duplicate

        assert len(gset.items) == 2
        assert "a" in gset.items
        assert "b" in gset.items

    def test_merge_union(self):
        """Test merging is union."""
        gset1 = GSet(items={"a", "b"})
        gset2 = GSet(items={"b", "c"})

        result = gset1.merge(gset2)

        assert result.items == {"a", "b", "c"}

    def test_to_dict_and_from_dict(self):
        """Test serialization."""
        gset = GSet(items={"a", "b"})
        data = gset.to_dict()

        restored = GSet.from_dict(data)
        assert restored.items == {"a", "b"}


class TestTwoPhaseSet:
    """Tests for Two-Phase Set."""

    def test_add_items(self):
        """Test adding items."""
        tps = TwoPhaseSet()
        assert tps.add("a") is True
        assert tps.add("b") is True

        assert tps.items == {"a", "b"}

    def test_remove_items(self):
        """Test removing items."""
        tps = TwoPhaseSet()
        tps.add("a")
        tps.add("b")

        assert tps.remove("a") is True
        assert tps.items == {"b"}

    def test_cannot_readd_removed(self):
        """Test that removed items cannot be re-added."""
        tps = TwoPhaseSet()
        tps.add("a")
        tps.remove("a")

        assert tps.add("a") is False
        assert "a" not in tps.items

    def test_merge(self):
        """Test merging two-phase sets."""
        tps1 = TwoPhaseSet()
        tps1.add("a")
        tps1.add("b")

        tps2 = TwoPhaseSet()
        tps2.add("b")
        tps2.add("c")
        tps2.remove("b")

        result = tps1.merge(tps2)

        # b is in removed in tps2, so it's removed in result
        assert result.items == {"a", "c"}

    def test_to_dict_and_from_dict(self):
        """Test serialization."""
        tps = TwoPhaseSet()
        tps.add("a")
        tps.add("b")
        tps.remove("a")

        data = tps.to_dict()
        restored = TwoPhaseSet.from_dict(data)

        assert restored.items == {"b"}


class TestWALChange:
    """Tests for WALChange dataclass."""

    def test_to_dict(self):
        """Test serialization."""
        change = WALChange(
            sequence=1,
            table="users",
            operation="INSERT",
            row_id=100,
            new_values={"name": "John"},
        )

        data = change.to_dict()

        assert data["sequence"] == 1
        assert data["table"] == "users"
        assert data["operation"] == "INSERT"

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "sequence": 2,
            "table": "items",
            "operation": "UPDATE",
            "row_id": 50,
            "old_values": {"val": 1},
            "new_values": {"val": 2},
        }

        change = WALChange.from_dict(data)

        assert change.sequence == 2
        assert change.table == "items"
        assert change.old_values == {"val": 1}


class TestSchemaVersion:
    """Tests for SchemaVersion."""

    def test_to_dict(self):
        """Test serialization."""
        sv = SchemaVersion(
            version=1,
            tables={"users": ["id", "name"]},
            created_at="2024-01-01",
            migrations=["initial"],
        )

        data = sv.to_dict()

        assert data["version"] == 1
        assert "users" in data["tables"]

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "version": 2,
            "tables": {"items": ["id", "value"]},
            "created_at": "2024-02-01",
        }

        sv = SchemaVersion.from_dict(data)

        assert sv.version == 2
        assert "items" in sv.tables


class TestTableSyncState:
    """Tests for TableSyncState."""

    def test_to_dict(self):
        """Test serialization."""
        state = TableSyncState(
            table_name="users",
            row_count=100,
            last_row_id=150,
            checksum="abc123",
            schema_hash="def456",
            last_modified_ms=1000.0,
        )

        data = state.to_dict()

        assert data["table_name"] == "users"
        assert data["row_count"] == 100

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "table_name": "items",
            "row_count": 50,
            "last_row_id": 75,
            "checksum": "xyz",
            "schema_hash": "abc",
            "last_modified_ms": 2000.0,
        }

        state = TableSyncState.from_dict(data)

        assert state.table_name == "items"
        assert state.row_count == 50


class TestWALChangeTracker:
    """Tests for WAL change tracking."""

    @pytest.fixture
    def db_conn(self, tmp_path):
        """Create a test database."""
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)

        # Create a test table
        conn.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value INTEGER
            )
        """)
        conn.commit()

        yield conn
        conn.close()

    def test_setup_creates_tables(self, db_conn):
        """Test that setup creates tracking tables."""
        tracker = WALChangeTracker(":memory:", ["test_table"])
        tracker.setup(db_conn)

        # Check changes table exists
        cursor = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='_sync_changes'"
        )
        assert cursor.fetchone() is not None

    def test_captures_insert(self, db_conn):
        """Test that INSERT is captured."""
        tracker = WALChangeTracker(":memory:", ["test_table"])
        tracker.setup(db_conn)

        # Insert a row
        db_conn.execute("INSERT INTO test_table (name, value) VALUES ('test', 42)")
        db_conn.commit()

        # Check changes
        changes = tracker.get_unsynced_changes(db_conn)
        assert len(changes) == 1
        assert changes[0].operation == "INSERT"
        assert changes[0].table == "test_table"

    def test_captures_update(self, db_conn):
        """Test that UPDATE is captured."""
        tracker = WALChangeTracker(":memory:", ["test_table"])
        tracker.setup(db_conn)

        # Insert then update
        db_conn.execute("INSERT INTO test_table (name, value) VALUES ('test', 42)")
        db_conn.execute("UPDATE test_table SET value = 100 WHERE name = 'test'")
        db_conn.commit()

        changes = tracker.get_unsynced_changes(db_conn)
        assert len(changes) == 2
        assert changes[1].operation == "UPDATE"

    def test_captures_delete(self, db_conn):
        """Test that DELETE is captured."""
        tracker = WALChangeTracker(":memory:", ["test_table"])
        tracker.setup(db_conn)

        # Insert then delete
        db_conn.execute("INSERT INTO test_table (name, value) VALUES ('test', 42)")
        db_conn.execute("DELETE FROM test_table WHERE name = 'test'")
        db_conn.commit()

        changes = tracker.get_unsynced_changes(db_conn)
        assert len(changes) == 2
        assert changes[1].operation == "DELETE"

    def test_mark_synced(self, db_conn):
        """Test marking changes as synced."""
        tracker = WALChangeTracker(":memory:", ["test_table"])
        tracker.setup(db_conn)

        db_conn.execute("INSERT INTO test_table (name, value) VALUES ('test', 42)")
        db_conn.commit()

        changes = tracker.get_unsynced_changes(db_conn)
        tracker.mark_synced(db_conn, [changes[0].sequence])

        # Should have no unsynced changes now
        changes = tracker.get_unsynced_changes(db_conn)
        assert len(changes) == 0


class TestSQLiteSyncManager:
    """Tests for SQLiteSyncManager."""

    @pytest.fixture
    def partition(self):
        return UserPartition(user_id="test_user")

    @pytest.fixture
    def db_and_conn(self, tmp_path):
        """Create test database and connection."""
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)

        # Create test tables
        conn.execute("""
            CREATE TABLE conversation_logs (
                id INTEGER PRIMARY KEY,
                session_id TEXT,
                transcript TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()

        yield db_path, conn
        conn.close()

    @pytest.fixture
    def sync_manager(self, db_and_conn, partition, tmp_path):
        db_path, _ = db_and_conn
        config = SQLiteSyncConfig(
            storage_backend="local",
            bucket_or_container=str(tmp_path / "sqlite_sync"),
            tracked_tables=["conversation_logs", "user_preferences"],
        )
        return SQLiteSyncManager(
            db_path=db_path,
            config=config,
            partition=partition,
            node_id="test_node",
        )

    async def test_initialize(self, sync_manager, db_and_conn):
        """Test initializing sync manager."""
        _, conn = db_and_conn
        await sync_manager.initialize(conn)

        assert sync_manager._initialized is True

    async def test_get_table_state(self, sync_manager, db_and_conn):
        """Test getting table state."""
        _, conn = db_and_conn
        await sync_manager.initialize(conn)

        # Insert some data
        conn.execute("INSERT INTO conversation_logs (session_id, transcript) VALUES ('s1', 'hello')")
        conn.commit()

        state = await sync_manager.get_table_state(conn, "conversation_logs")

        assert state.table_name == "conversation_logs"
        assert state.row_count == 1

    async def test_push_empty(self, sync_manager, db_and_conn):
        """Test pushing with no changes."""
        _, conn = db_and_conn
        await sync_manager.initialize(conn)

        result = await sync_manager.push(conn)

        assert result.success is True
        assert result.pushed_count == 0

    async def test_push_with_changes(self, sync_manager, db_and_conn):
        """Test pushing changes."""
        _, conn = db_and_conn
        await sync_manager.initialize(conn)

        # Make changes
        conn.execute("INSERT INTO conversation_logs (session_id, transcript) VALUES ('s1', 'hello')")
        conn.commit()

        result = await sync_manager.push(conn)

        assert result.success is True
        assert result.pushed_count >= 1

    async def test_pull_empty_storage(self, sync_manager, db_and_conn):
        """Test pulling from empty storage."""
        _, conn = db_and_conn
        await sync_manager.initialize(conn)

        result = await sync_manager.pull(conn)

        assert result.success is True
        assert result.pulled_count == 0

    async def test_push_then_pull(self, sync_manager, db_and_conn, partition, tmp_path):
        """Test push then pull cycle."""
        db_path, conn = db_and_conn
        await sync_manager.initialize(conn)

        # Push some data
        conn.execute("INSERT INTO conversation_logs (session_id, transcript) VALUES ('s1', 'hello')")
        conn.commit()
        await sync_manager.push(conn)

        # Create new manager
        config = SQLiteSyncConfig(
            storage_backend="local",
            bucket_or_container=str(tmp_path / "sqlite_sync"),
            tracked_tables=["conversation_logs", "user_preferences"],
        )
        new_manager = SQLiteSyncManager(
            db_path=db_path,
            config=config,
            partition=partition,
            node_id="other_node",
        )
        await new_manager.initialize(conn)

        result = await new_manager.pull(conn)

        assert result.success is True

    async def test_sync_bidirectional(self, sync_manager, db_and_conn):
        """Test bidirectional sync."""
        _, conn = db_and_conn
        await sync_manager.initialize(conn)

        conn.execute("INSERT INTO conversation_logs (session_id, transcript) VALUES ('s1', 'test')")
        conn.commit()

        result = await sync_manager.sync(conn)

        assert result.success is True

    def test_health(self, sync_manager):
        """Test health status."""
        health = sync_manager.health()

        assert "partition_id" in health
        assert "node_id" in health
        assert health["node_id"] == "test_node"


class TestSQLiteSyncConfig:
    """Tests for SQLiteSyncConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = SQLiteSyncConfig()

        assert config.storage_backend == "local"
        assert config.encrypt_data is True
        assert "conversation_logs" in config.tracked_tables

    def test_custom_config(self):
        """Test custom configuration."""
        config = SQLiteSyncConfig(
            storage_backend="s3",
            bucket_or_container="my-bucket",
            tracked_tables=["custom_table"],
            encrypt_data=False,
        )

        assert config.storage_backend == "s3"
        assert config.encrypt_data is False


class TestCreateSqliteSyncManager:
    """Tests for factory function."""

    def test_create_with_defaults(self, tmp_path):
        """Test factory with default parameters."""
        partition = UserPartition(user_id="test_user")
        db_path = str(tmp_path / "test.db")

        manager = create_sqlite_sync_manager(db_path, partition, "test_node")

        assert manager.node_id == "test_node"
        assert manager.partition == partition

    def test_create_with_custom_storage(self, tmp_path):
        """Test factory with custom storage."""
        partition = UserPartition(user_id="test_user")
        db_path = str(tmp_path / "test.db")

        manager = create_sqlite_sync_manager(
            db_path,
            partition,
            "test_node",
            bucket_or_container="custom-bucket",
        )

        assert manager.config.bucket_or_container == "custom-bucket"
