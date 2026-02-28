import sqlite3
import threading
import logging
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger("sqlite-manager")

@dataclass
class ConversationLog:
    rowid: Optional[int] = None
    session_id: Optional[str] = None
    device_id: Optional[str] = None
    timestamp: Optional[str] = None
    transcript: str = ""
    summary: Optional[str] = None
    user_label: Optional[str] = None
    scene_graph_ref: Optional[str] = None
    scene_graph: Optional[str] = None
    expiry: Optional[str] = None
    embedding_status: str = 'completed'
    privacy_flag: str = 'normal'
    has_raw_image: bool = False
    has_raw_audio: bool = False
    vector_dim: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class SQLiteManager:
    """Thread-safe singleton for managing SQLite storage of conversational metadata."""
    _instance = None
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SQLiteManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: str = "./data/app_state.db"):
        with self._lock:
            if self._initialized:
                return
            
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = None
            self._init_db()
            self._initialized = True

    def _get_conn(self) -> sqlite3.Connection:
        """Returns a thread-local connection or a new one if not exists."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                isolation_level=None
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        return self._conn

    def _init_db(self):
        """Initializes the database schema."""
        try:
            conn = self._get_conn()
            with self._lock:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_logs (
                        rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        device_id TEXT,
                        timestamp TEXT DEFAULT (datetime('now')),
                        transcript TEXT NOT NULL,
                        summary TEXT,
                        user_label TEXT,
                        scene_graph_ref TEXT,
                        scene_graph TEXT,
                        expiry TEXT,
                        embedding_status TEXT DEFAULT 'completed',
                        privacy_flag TEXT DEFAULT 'normal',
                        has_raw_image INTEGER DEFAULT 0,
                        has_raw_audio INTEGER DEFAULT 0,
                        vector_dim INTEGER
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT DEFAULT (datetime('now'))
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS engine_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT DEFAULT (datetime('now'))
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS telemetry_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT DEFAULT (datetime('now')),
                        event_type TEXT NOT NULL,
                        payload TEXT
                    )
                """)
                logger.info(f"Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def insert_conversation(
        self, 
        session_id: str, 
        transcript: str, 
        summary: Optional[str] = None, 
        scene_graph_ref: Optional[str] = None,
        expiry: Optional[str] = None,
        user_label: Optional[str] = None,
        device_id: Optional[str] = None,
        scene_graph: Optional[str] = None,
        embedding_status: str = 'completed',
        privacy_flag: str = 'normal',
        has_raw_image: bool = False,
        has_raw_audio: bool = False,
        vector_dim: Optional[int] = None
    ) -> int:
        """Persists a new conversation record and returns its rowid."""
        with self._lock:
            try:
                conn = self._get_conn()
                cursor = conn.cursor()
                cursor.execute("BEGIN IMMEDIATE")
                cursor.execute(
                    """
                    INSERT INTO conversation_logs (
                        session_id, device_id, transcript, summary, user_label, 
                        scene_graph_ref, scene_graph, expiry, embedding_status, 
                        privacy_flag, has_raw_image, has_raw_audio, vector_dim
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id, device_id, transcript, summary, user_label,
                        scene_graph_ref, scene_graph, expiry, embedding_status,
                        privacy_flag, 1 if has_raw_image else 0, 1 if has_raw_audio else 0, vector_dim
                    )
                )
                rowid = cursor.lastrowid
                conn.execute("COMMIT")
                logger.debug(f"Inserted conversation record with rowid {rowid}")
                return rowid
            except sqlite3.Error as e:
                if self._conn:
                    self._conn.execute("ROLLBACK")
                logger.error(f"Failed to insert conversation: {e}")
                return -1

    def get_conversation(self, rowid: int) -> Optional[ConversationLog]:
        """Retrieves a single conversation record by its rowid."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT rowid, * FROM conversation_logs WHERE rowid = ?",
                (rowid,)
            )
            row = cursor.fetchone()
            if row:
                data = dict(row)
                data['has_raw_image'] = bool(data['has_raw_image'])
                data['has_raw_audio'] = bool(data['has_raw_audio'])
                return ConversationLog(**data)
            return None
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve conversation {rowid}: {e}")
            return None

    def get_conversations_by_ids(self, rowids: List[int]) -> List[ConversationLog]:
        """Bulk retrieves conversation logs by their rowids."""
        if not rowids:
            return []
        
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(rowids))
            query = f"SELECT rowid, * FROM conversation_logs WHERE rowid IN ({placeholders})"
            cursor.execute(query, rowids)
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                data = dict(row)
                data['has_raw_image'] = bool(data['has_raw_image'])
                data['has_raw_audio'] = bool(data['has_raw_audio'])
                logs.append(ConversationLog(**data))
            
            id_to_log = {log.rowid: log for log in logs}
            return [id_to_log[rid] for rid in rowids if rid in id_to_log]
            
        except sqlite3.Error as e:
            logger.error(f"Failed bulk retrieval: {e}")
            return []

    def get_conversations_by_session(
        self, 
        session_id: str, 
        limit: int = 50
    ) -> List[ConversationLog]:
        """Retrieves all conversation logs for a specific session."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT rowid, * FROM conversation_logs WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit)
            )
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                data = dict(row)
                data['has_raw_image'] = bool(data['has_raw_image'])
                data['has_raw_audio'] = bool(data['has_raw_audio'])
                logs.append(ConversationLog(**data))
            return logs
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve logs for session {session_id}: {e}")
            return []

    def get_recent_conversations(
        self, 
        hours: float = 24.0, 
        limit: int = 20
    ) -> List[ConversationLog]:
        """Retrieves conversation logs from the last N hours."""
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT rowid, * FROM conversation_logs WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?",
                (cutoff, limit)
            )
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                data = dict(row)
                data['has_raw_image'] = bool(data['has_raw_image'])
                data['has_raw_audio'] = bool(data['has_raw_audio'])
                logs.append(ConversationLog(**data))
            return logs
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve recent logs: {e}")
            return []

    def update_preference(self, key: str, value: str):
        """Stores or updates a user preference."""
        with self._lock:
            try:
                conn = self._get_conn()
                conn.execute(
                    "INSERT OR REPLACE INTO user_preferences (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                    (key, value)
                )
            except sqlite3.Error as e:
                logger.error(f"Failed to update preference {key}: {e}")

    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves a specific user preference."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else default
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve preference {key}: {e}")
            return default

    def log_telemetry(self, event_type: str, payload: str):
        """Records a structured telemetry event."""
        with self._lock:
            try:
                conn = self._get_conn()
                conn.execute(
                    "INSERT INTO telemetry_logs (event_type, payload) VALUES (?, ?)",
                    (event_type, payload)
                )
            except sqlite3.Error as e:
                logger.error(f"Failed to log telemetry: {e}")

    def get_engine_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Fetches system-level engine configurations."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM engine_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else default
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve engine setting {key}: {e}")
            return default

    def close(self):
        """Closes the database connection."""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
                self._initialized = False
