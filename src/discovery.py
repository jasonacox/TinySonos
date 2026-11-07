"""
Sonos speaker discovery helpers for TinySonos.

soco.discover() returns None (not an empty set) when no speakers answer,
so callers must not wrap it in list() directly.
"""

import logging
from typing import Callable, List, Optional

import soco

log = logging.getLogger(__name__)


def discover_speakers(discover: Callable = soco.discover) -> List:
    """Return the list of discovered speakers (empty if none were found)."""
    found = discover()
    return list(found) if found else []


def find_coordinator(discover: Callable = soco.discover) -> Optional[object]:
    """Return the group coordinator of the first discovered speaker, or None."""
    speakers = discover_speakers(discover)
    if not speakers:
        log.warning("No Sonos speakers found on the network")
        return None
    return speakers[0].group.coordinator
