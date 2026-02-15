"""
Places Search Tool for Ally Vision Assistant

Uses OpenStreetMap Nominatim (free, no API key) for location
and points-of-interest searches.  Zero Google dependencies.
"""

import logging
from typing import Optional

# Simple logger without custom handler
logger = logging.getLogger("places-search")


class PlacesSearch:
    """Handler for OpenStreetMap Nominatim places search."""

    def __init__(self):
        """Initialise the Nominatim geocoder."""
        self._initialized = False
        self._geolocator = None

        try:
            from geopy.geocoders import Nominatim

            self._geolocator = Nominatim(user_agent="ally-vision-assistant")
            self._initialized = True
            logger.info("Places search initialised (OpenStreetMap Nominatim)")
        except Exception as e:
            logger.warning(f"Places search initialisation failed: {e}")
            self._initialized = False

    async def search_places(self, query: str) -> str:
        """
        Search for places using OpenStreetMap Nominatim.

        Args:
            query: Search query for places

        Returns:
            Results as string
        """
        if not self._initialized or self._geolocator is None:
            return (
                "Places search is not available. "
                "Please install geopy: pip install geopy"
            )

        try:
            logger.info(f"Searching places: {query}")
            # Use geocode with exactly_one=False to get multiple results
            locations = self._geolocator.geocode(
                query, exactly_one=False, limit=5, addressdetails=True
            )

            if not locations:
                return f"No places found for '{query}'."

            results = []
            for i, loc in enumerate(locations, 1):
                addr = loc.raw.get("address", {})
                parts = [loc.address]
                place_type = loc.raw.get("type", "unknown")
                results.append(
                    f"{i}. {parts[0]}\n   Type: {place_type}  |  "
                    f"Lat: {loc.latitude:.5f}, Lon: {loc.longitude:.5f}"
                )

            return "\n".join(results)

        except Exception as e:
            logger.error(f"Error searching places: {e}")
            return f"I encountered an error while searching for places: {str(e)}"