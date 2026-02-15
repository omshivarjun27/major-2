#!/usr/bin/env python
"""
Ally Vision Assistant - Entry Point
A voice and vision assistant for blind and visually impaired users.

Features:
- Real-time voice interaction with STT/TTS
- Visual scene analysis and description
- Spatial perception: object detection, depth estimation, micro-navigation
- Multi-tool integration: calendar, email, contacts, places, search
"""

import logging
import sys
import multiprocessing

# Fix Windows multiprocessing freeze issue
if sys.platform == "win32":
    multiprocessing.freeze_support()

# Load environment variables from .env
import os
from dotenv import load_dotenv
load_dotenv()
os.environ.setdefault("OPENAI_API_KEY", "ollama")
os.environ.setdefault("OPENAI_BASE_URL", "http://localhost:11434/v1")

# ── Structured logging (JSON in production, coloured text in dev) ─────
from shared.logging.logging_config import configure_logging
configure_logging(level="INFO")

# Fine-tune noisy loggers
for log_module in ["livekit", "livekit.agents"]: logging.getLogger(log_module).setLevel(logging.INFO)
for log_module in ["livekit.rtc", "primp", "httpx", "asyncio"]: logging.getLogger(log_module).setLevel(logging.WARNING)
logging.getLogger("livekit.plugins").setLevel(logging.DEBUG)
logging.getLogger("livekit.plugins.silero").setLevel(logging.ERROR)  # Suppress VAD realtime warnings
logging.getLogger("spatial-perception").setLevel(logging.INFO)  # Spatial perception logging

# ── Suppress benign Windows dev-watcher IPC error ──────────────────────
# The DuplexClosed / _read_ipc_task traceback comes from LiveKit's internal
# file-watcher subprocess IPC on Windows.  It is harmless and cannot be
# fixed in user code.  Filter it out so the console stays clean.
class _IPCErrorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(getattr(record, "msg", ""))
        # Suppress the _read_ipc_task wrapper error and its traceback
        if "_read_ipc_task" in msg:
            return False
        if "DuplexClosed" in msg or "IncompleteReadError" in msg:
            return False
        # Also check exc_text for tracebacks containing these strings
        exc = str(getattr(record, "exc_text", "") or "")
        if "DuplexClosed" in exc or "_read_ipc_task" in exc or "IncompleteReadError" in exc:
            return False
        return True

for _logger_name in ("livekit.agents", "livekit"):
    _lg = logging.getLogger(_logger_name)
    _lg.addFilter(_IPCErrorFilter())

# Import after environment variables are loaded
from livekit.agents import WorkerOptions, cli
from apps.realtime.agent import entrypoint
from shared.config import get_config, spatial_enabled

# Main application logger
logger = logging.getLogger("ally-vision-app")

if __name__ == "__main__":
    logger.info("Starting Ally Vision Assistant")
    
    # Log spatial perception status
    if spatial_enabled():
        logger.info("Spatial Perception: ENABLED (object detection, depth estimation, micro-navigation)")
    else:
        logger.info("Spatial Perception: DISABLED")
    
    # Run the application using the entrypoint from main.py
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint)) 