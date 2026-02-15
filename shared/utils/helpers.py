"""
Utility functions for Ally Vision Assistant

This module provides common utility functions used across tools,
especially for date/time operations and local data helpers.
"""

import logging
from datetime import datetime

# Simple logger without custom handler
logger = logging.getLogger("utils")


def get_current_date_time():
    """
    Get current date and time in a human-readable format.

    Returns:
        String formatted as YYYY-MM-DD HH:MM
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M")