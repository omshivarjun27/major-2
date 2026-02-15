"""
Calendar integration tool for Ally Vision Assistant

Local JSON-based calendar – no external services required.
Events are stored in a local ``calendar_events.json`` file.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from shared.config import get_config
from shared.utils.helpers import get_current_date_time

# Simple logger without custom handler
logger = logging.getLogger("calendar-tool")

# Default path for the local calendar store
_DEFAULT_CALENDAR_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "calendar_events.json",
)


class CalendarTool:
    """Handler for local JSON-based calendar."""

    def __init__(self, calendar_file: Optional[str] = None):
        """Initialise the local calendar handler."""
        self.calendar_file = calendar_file or _DEFAULT_CALENDAR_FILE
        self.is_ready = True
        self._ensure_file()
        logger.info(f"Calendar tool initialised (local store: {self.calendar_file})")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_file(self):
        """Create the calendar file if it does not exist."""
        if not os.path.exists(self.calendar_file):
            with open(self.calendar_file, "w") as f:
                json.dump([], f)

    def _load_events(self) -> List[Dict[str, Any]]:
        """Load all events from disk."""
        try:
            with open(self.calendar_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_events(self, events: List[Dict[str, Any]]):
        """Persist events to disk."""
        with open(self.calendar_file, "w") as f:
            json.dump(events, f, indent=2, default=str)

    # ------------------------------------------------------------------
    # Public API (same interface as before)
    # ------------------------------------------------------------------

    async def manage_calendar(self, action: str, **kwargs) -> str:
        """
        Unified method to manage calendar operations.

        Args:
            action: The action to perform ("add_event" or "get_events")
            **kwargs: Arguments specific to the action
                For add_event: title, description, start_time
                For get_events: start_date, end_date

        Returns:
            Result message from the performed action
        """
        if not self.is_ready:
            return "Calendar tool is not properly initialised."

        try:
            if action == "add_event":
                if "start_time" not in kwargs or not kwargs["start_time"]:
                    kwargs["start_time"] = get_current_date_time()
                    logger.info(f"Using current time for new event: {kwargs['start_time']}")
                return await self._add_event(**kwargs)
            elif action == "get_events":
                return await self._get_events(**kwargs)
            else:
                return f"Unsupported calendar action: {action}"
        except Exception as e:
            error_msg = f"Unexpected error in calendar action {action}: {e}"
            logger.error(error_msg)
            return f"An unexpected error occurred: {str(e)}"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _add_event(self, title: str, description: str, start_time: str) -> str:
        """Add an event to the local calendar store."""
        try:
            event_datetime = datetime.fromisoformat(start_time)
            event_id = uuid.uuid4().hex[:12]

            event = {
                "id": event_id,
                "summary": title,
                "description": description,
                "start": event_datetime.isoformat(),
                "end": (event_datetime + timedelta(hours=1)).isoformat(),
            }

            events = self._load_events()
            events.append(event)
            self._save_events(events)

            logger.info(f"Event created: {title} at {start_time}")
            return f"Event created successfully. Event ID: {event_id}"

        except Exception as error:
            error_msg = f"Error creating calendar event: {error}"
            logger.error(error_msg)
            return f"An error occurred: {error}"

    async def _get_events(self, start_date: str, end_date: str) -> str:
        """Retrieve events within the given date range."""
        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)

            events = self._load_events()
            matching = []
            for ev in events:
                ev_start = datetime.fromisoformat(ev["start"])
                if start_dt <= ev_start <= end_dt:
                    desc = ev.get("description", "No description")
                    matching.append(
                        f"Event: {ev['summary']}, Description: {desc}, Start: {ev['start']}"
                    )

            if not matching:
                return "No events found in the specified time range."

            logger.info(f"Retrieved {len(matching)} events")
            return "\n".join(matching)

        except Exception as error:
            error_msg = f"Error retrieving calendar events: {error}"
            logger.error(error_msg)
            return f"An error occurred: {error}"