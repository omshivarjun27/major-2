"""
Consent Audit Log — JSONL trail for face consent events.
"""

from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List


@dataclass
class AuditEntry:
    """Single consent/audit record."""

    timestamp: str
    event_type: str
    person_id: str
    details: Dict[str, Any]


@contextmanager
def _locked_file(file_obj) -> Iterator[None]:
    if os.name == "nt":
        import msvcrt

        file_obj.seek(0)
        msvcrt.locking(file_obj.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            file_obj.seek(0)
            msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)


class ConsentAuditLog:
    """Append-only JSONL audit log for consent events."""

    def __init__(self, audit_dir: str = "data/consent") -> None:
        self._audit_dir = Path(audit_dir)
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._audit_path = self._audit_dir / "face_audit.jsonl"
        self._thread_lock = threading.Lock()

    def log(self, entry: AuditEntry) -> None:
        payload = json.dumps(asdict(entry))
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        with self._thread_lock:
            with open(self._audit_path, "a+", encoding="utf-8") as audit_file:
                with _locked_file(audit_file):
                    audit_file.seek(0, os.SEEK_END)
                    audit_file.write(payload + "\n")
                    audit_file.flush()

    def read_entries(self) -> List[AuditEntry]:
        if not self._audit_path.exists():
            return []
        entries: List[AuditEntry] = []
        with self._thread_lock:
            with open(self._audit_path, "r", encoding="utf-8") as audit_file:
                with _locked_file(audit_file):
                    for line in audit_file:
                        line = line.strip()
                        if not line:
                            continue
                        data = json.loads(line)
                        entries.append(
                            AuditEntry(
                                timestamp=data.get("timestamp", ""),
                                event_type=data.get("event_type", ""),
                                person_id=data.get("person_id", ""),
                                details=data.get("details", {}),
                            )
                        )
        return entries
