"""
VQA Engine - Memory Module
===========================

RAG-ready session memory for storing and retrieving
past scene perceptions and VQA interactions.
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .scene_graph import SceneGraph, ObstacleRecord
from .vqa_reasoner import VQARequest, VQAResponse

logger = logging.getLogger("vqa-memory")


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class MemoryConfig:
    """Configuration for VQA memory system."""
    
    # Storage settings
    max_entries: int = 1000             # Maximum entries in memory
    persist_path: Optional[str] = None  # Path to persist memory (None = in-memory only)
    
    # TTL settings
    entry_ttl_sec: float = 3600.0       # 1 hour default TTL
    session_ttl_sec: float = 86400.0    # 24 hour session TTL
    
    # Retrieval settings
    similarity_threshold: float = 0.7   # Minimum similarity for retrieval
    max_retrieval_results: int = 5      # Maximum results per query
    
    # Embedding settings (for future RAG)
    use_embeddings: bool = False        # Enable embedding-based retrieval
    embedding_model: str = "all-MiniLM-L6-v2"


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class SceneEntry:
    """
    Single scene perception entry in memory.
    """
    id: str
    timestamp: float
    session_id: str
    
    # Scene data
    scene_graph_json: str
    obstacle_count: int
    obstacle_classes: List[str]
    has_critical: bool
    
    # Optional VQA data
    question: Optional[str] = None
    answer: Optional[str] = None
    
    # Metadata
    image_hash: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "obstacle_count": self.obstacle_count,
            "obstacle_classes": self.obstacle_classes,
            "has_critical": self.has_critical,
            "question": self.question,
            "answer": self.answer,
            "tags": self.tags,
        }
    
    @classmethod
    def from_scene_graph(
        cls,
        scene: SceneGraph,
        session_id: str,
        question: Optional[str] = None,
        answer: Optional[str] = None,
    ) -> "SceneEntry":
        """Create entry from scene graph."""
        entry_id = f"{session_id}_{int(time.time()*1000)}"
        
        return cls(
            id=entry_id,
            timestamp=time.time(),
            session_id=session_id,
            scene_graph_json=json.dumps(scene.to_dict()),
            obstacle_count=len(scene.obstacles),
            obstacle_classes=list(set(o.class_name for o in scene.obstacles)),
            has_critical=scene.to_dict().get("has_critical", False),
            question=question,
            answer=answer,
        )


@dataclass
class Session:
    """
    VQA session tracking user interaction history.
    """
    id: str
    created_at: float
    last_active: float
    entry_count: int = 0
    critical_count: int = 0
    
    # Session stats
    total_obstacles_seen: int = 0
    unique_classes: set = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "entry_count": self.entry_count,
            "critical_count": self.critical_count,
            "total_obstacles_seen": self.total_obstacles_seen,
            "unique_classes": list(self.unique_classes),
            "duration_sec": round(self.last_active - self.created_at, 1),
        }


# ============================================================================
# Memory Store
# ============================================================================

class VQAMemory:
    """
    Main memory class for storing and retrieving VQA sessions.
    Supports both in-memory and persistent storage.
    
    Usage:
        memory = VQAMemory()
        session = memory.create_session()
        memory.store(scene_entry)
        results = memory.retrieve("what obstacles")
    """
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        
        # In-memory storage
        self._entries: Dict[str, SceneEntry] = {}
        self._sessions: Dict[str, Session] = {}
        self._entry_index: Dict[str, List[str]] = {}  # session_id -> entry_ids
        
        # Class-based index for fast retrieval
        self._class_index: Dict[str, List[str]] = {}  # class_name -> entry_ids
        
        # Load from disk if configured
        if self.config.persist_path:
            self._load_from_disk()
    
    # ========================================================================
    # Session Management
    # ========================================================================
    
    def create_session(self, session_id: Optional[str] = None) -> Session:
        """Create a new VQA session."""
        if not session_id:
            session_id = f"session_{int(time.time()*1000)}"
        
        session = Session(
            id=session_id,
            created_at=time.time(),
            last_active=time.time(),
        )
        
        self._sessions[session_id] = session
        self._entry_index[session_id] = []
        
        logger.debug(f"Created session: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get existing session by ID."""
        return self._sessions.get(session_id)
    
    def get_or_create_session(self, session_id: str) -> Session:
        """Get existing session or create new one."""
        if session_id in self._sessions:
            return self._sessions[session_id]
        return self.create_session(session_id)
    
    def list_sessions(self, active_only: bool = True) -> List[Session]:
        """List all sessions."""
        sessions = list(self._sessions.values())
        
        if active_only:
            cutoff = time.time() - self.config.session_ttl_sec
            sessions = [s for s in sessions if s.last_active > cutoff]
        
        return sorted(sessions, key=lambda s: s.last_active, reverse=True)
    
    # ========================================================================
    # Entry Storage
    # ========================================================================
    
    def store(
        self,
        scene: SceneGraph,
        session_id: str,
        question: Optional[str] = None,
        answer: Optional[str] = None,
    ) -> SceneEntry:
        """
        Store a scene perception in memory.
        
        Args:
            scene: Scene graph to store
            session_id: Session to associate with
            question: Optional VQA question
            answer: Optional VQA answer
            
        Returns:
            Created SceneEntry
        """
        # Get or create session
        session = self.get_or_create_session(session_id)
        
        # Create entry
        entry = SceneEntry.from_scene_graph(scene, session_id, question, answer)
        
        # Store entry
        self._entries[entry.id] = entry
        self._entry_index[session_id].append(entry.id)
        
        # Update indexes
        for cls in entry.obstacle_classes:
            if cls not in self._class_index:
                self._class_index[cls] = []
            self._class_index[cls].append(entry.id)
        
        # Update session stats
        session.entry_count += 1
        session.last_active = time.time()
        session.total_obstacles_seen += entry.obstacle_count
        session.unique_classes.update(entry.obstacle_classes)
        if entry.has_critical:
            session.critical_count += 1
        
        # Enforce max entries
        self._enforce_limits()
        
        # Persist if configured
        if self.config.persist_path:
            self._save_to_disk()
        
        logger.debug(f"Stored entry {entry.id} in session {session_id}")
        return entry
    
    def store_vqa_response(
        self,
        entry_id: str,
        response: VQAResponse,
    ) -> bool:
        """Update entry with VQA response."""
        if entry_id not in self._entries:
            return False
        
        entry = self._entries[entry_id]
        entry.answer = response.answer
        
        return True
    
    # ========================================================================
    # Retrieval
    # ========================================================================
    
    def retrieve(
        self,
        query: str,
        session_id: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> List[SceneEntry]:
        """
        Retrieve relevant entries based on query.
        
        Args:
            query: Search query (class name, keyword, or question)
            session_id: Limit to specific session (optional)
            max_results: Maximum results to return
            
        Returns:
            List of matching SceneEntries
        """
        max_results = max_results or self.config.max_retrieval_results
        results = []
        
        # Get candidate entries
        if session_id:
            entry_ids = self._entry_index.get(session_id, [])
        else:
            entry_ids = list(self._entries.keys())
        
        # Search by class name
        query_lower = query.lower()
        for class_name, class_entry_ids in self._class_index.items():
            if class_name.lower() in query_lower or query_lower in class_name.lower():
                for eid in class_entry_ids:
                    if eid in entry_ids and eid not in [r.id for r in results]:
                        results.append(self._entries[eid])
        
        # Search by question/answer text
        for eid in entry_ids:
            entry = self._entries[eid]
            if entry.id in [r.id for r in results]:
                continue
            
            if entry.question and query_lower in entry.question.lower():
                results.append(entry)
            elif entry.answer and query_lower in entry.answer.lower():
                results.append(entry)
        
        # Sort by timestamp (most recent first)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        
        return results[:max_results]
    
    def get_session_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> List[SceneEntry]:
        """Get all entries for a session."""
        entry_ids = self._entry_index.get(session_id, [])
        entries = [self._entries[eid] for eid in entry_ids if eid in self._entries]
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]
    
    def get_recent_obstacles(
        self,
        session_id: str,
        seconds: float = 30.0,
    ) -> List[str]:
        """Get obstacle classes seen in recent seconds."""
        cutoff = time.time() - seconds
        entry_ids = self._entry_index.get(session_id, [])
        
        classes = set()
        for eid in reversed(entry_ids):  # Most recent first
            entry = self._entries.get(eid)
            if not entry:
                continue
            if entry.timestamp < cutoff:
                break
            classes.update(entry.obstacle_classes)
        
        return list(classes)
    
    # ========================================================================
    # Replay Support
    # ========================================================================
    
    def get_replay_data(
        self,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get session data in replay format.
        
        Returns list of frames with timestamps and scene data.
        """
        entries = self.get_session_history(session_id, limit=1000)
        entries.reverse()  # Chronological order
        
        replay_data = []
        for entry in entries:
            replay_data.append({
                "timestamp": entry.timestamp,
                "timestamp_human": datetime.fromtimestamp(entry.timestamp).isoformat(),
                "scene": json.loads(entry.scene_graph_json),
                "question": entry.question,
                "answer": entry.answer,
            })
        
        return replay_data
    
    def export_session(
        self,
        session_id: str,
        output_path: str,
    ) -> bool:
        """Export session to JSON file."""
        session = self.get_session(session_id)
        if not session:
            return False
        
        data = {
            "session": session.to_dict(),
            "entries": self.get_replay_data(session_id),
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        return True
    
    # ========================================================================
    # Housekeeping
    # ========================================================================
    
    def _enforce_limits(self):
        """Remove old entries if over limit."""
        if len(self._entries) <= self.config.max_entries:
            return
        
        # Sort by timestamp
        sorted_entries = sorted(
            self._entries.values(),
            key=lambda e: e.timestamp,
        )
        
        # Remove oldest entries
        remove_count = len(self._entries) - self.config.max_entries
        for entry in sorted_entries[:remove_count]:
            self._remove_entry(entry.id)
    
    def _remove_entry(self, entry_id: str):
        """Remove entry from all indexes."""
        if entry_id not in self._entries:
            return
        
        entry = self._entries[entry_id]
        
        # Remove from session index
        if entry.session_id in self._entry_index:
            if entry_id in self._entry_index[entry.session_id]:
                self._entry_index[entry.session_id].remove(entry_id)
        
        # Remove from class index
        for cls in entry.obstacle_classes:
            if cls in self._class_index and entry_id in self._class_index[cls]:
                self._class_index[cls].remove(entry_id)
        
        # Remove entry
        del self._entries[entry_id]
    
    def clear_session(self, session_id: str):
        """Clear all entries for a session."""
        entry_ids = list(self._entry_index.get(session_id, []))
        for eid in entry_ids:
            self._remove_entry(eid)
        
        if session_id in self._sessions:
            del self._sessions[session_id]
        if session_id in self._entry_index:
            del self._entry_index[session_id]
    
    def clear_all(self):
        """Clear all memory."""
        self._entries.clear()
        self._sessions.clear()
        self._entry_index.clear()
        self._class_index.clear()
    
    # ========================================================================
    # Persistence
    # ========================================================================
    
    def _save_to_disk(self):
        """Save memory to disk."""
        if not self.config.persist_path:
            return
        
        path = Path(self.config.persist_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "sessions": {sid: s.to_dict() for sid, s in self._sessions.items()},
            "entries": {eid: e.to_dict() for eid, e in self._entries.items()},
            "saved_at": time.time(),
        }
        
        with open(path, "w") as f:
            json.dump(data, f)
    
    def _load_from_disk(self):
        """Load memory from disk."""
        if not self.config.persist_path:
            return
        
        path = Path(self.config.persist_path)
        if not path.exists():
            return
        
        try:
            with open(path, "r") as f:
                data = json.load(f)
            
            # Restore sessions
            for sid, sdata in data.get("sessions", {}).items():
                session = Session(
                    id=sdata["id"],
                    created_at=sdata["created_at"],
                    last_active=sdata["last_active"],
                    entry_count=sdata.get("entry_count", 0),
                    critical_count=sdata.get("critical_count", 0),
                    total_obstacles_seen=sdata.get("total_obstacles_seen", 0),
                    unique_classes=set(sdata.get("unique_classes", [])),
                )
                self._sessions[sid] = session
                self._entry_index[sid] = []
            
            # Restore entries
            for eid, edata in data.get("entries", {}).items():
                entry = SceneEntry(
                    id=edata["id"],
                    timestamp=edata["timestamp"],
                    session_id=edata["session_id"],
                    scene_graph_json="{}",  # Not stored in summary
                    obstacle_count=edata["obstacle_count"],
                    obstacle_classes=edata["obstacle_classes"],
                    has_critical=edata["has_critical"],
                    question=edata.get("question"),
                    answer=edata.get("answer"),
                    tags=edata.get("tags", []),
                )
                self._entries[eid] = entry
                
                if entry.session_id in self._entry_index:
                    self._entry_index[entry.session_id].append(eid)
                
                for cls in entry.obstacle_classes:
                    if cls not in self._class_index:
                        self._class_index[cls] = []
                    self._class_index[cls].append(eid)
            
            logger.info(f"Loaded {len(self._entries)} entries from disk")
            
        except Exception as e:
            logger.error(f"Failed to load memory from disk: {e}")
    
    # ========================================================================
    # Stats
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "total_entries": len(self._entries),
            "total_sessions": len(self._sessions),
            "active_sessions": len(self.list_sessions(active_only=True)),
            "unique_classes": len(self._class_index),
            "memory_usage_estimate_kb": self._estimate_memory_usage(),
        }
    
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in KB."""
        # Rough estimate: 500 bytes per entry
        return (len(self._entries) * 500) // 1024
