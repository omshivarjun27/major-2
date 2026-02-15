"""
Backward-compatible alias for places_search module.

The PlacesSearch class was moved to places_search.py to accurately
reflect that it uses OpenStreetMap Nominatim (not Google).
"""
from .places_search import PlacesSearch

__all__ = ["PlacesSearch"]