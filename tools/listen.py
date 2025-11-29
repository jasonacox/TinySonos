#!/usr/bin/env python3
"""
Sonos Event Monitor

This tool subscribes to Sonos events and displays real-time updates from the speaker.
Useful for debugging and understanding how Sonos reports state changes.

Monitors:
- renderingControl events (volume changes, mute state, etc.)
- avTransport events (playback state: PLAYING, PAUSED_PLAYBACK, TRANSITIONING, STOPPED)

Usage:
    python3 listen.py

Press Ctrl+C to stop monitoring.

Example Output:
    Living Room
    ** renderingControl **
    {'volume': {'LF': '100', 'Master': '15', 'RF': '100'}}
    
    ** avTransport **
    {'transport_state': 'PLAYING'}
"""

from queue import Empty
from soco.events import event_listener
import logging
logging.basicConfig()
import soco
from pprint import pprint

print("Discovering Sonos speakers...")
# Pick a device at random and use it to get the group coordinator
device = soco.discover().pop().group.coordinator
print(f"Monitoring: {device.player_name}")
print("Press Ctrl+C to stop\n")

# Subscribe to events
sub = device.renderingControl.subscribe()
sub2 = device.avTransport.subscribe()

# Monitor events in real-time
while True:
    try:
        # Check for volume/rendering events
        event = sub.events.get(timeout=0.5)
        pprint("** renderingControl **")
        pprint(event.variables)
        # Example: {'volume': {'LF': '100', 'Master': '6', 'RF': '100'}}
    except Empty:
        pass
    
    try:
        # Check for transport/playback events
        event = sub2.events.get(timeout=0.5)
        pprint("** avTransport **")
        pprint(event.variables)
        # Example states: 'transport_state': 'PAUSED_PLAYBACK', 'TRANSITIONING', 'PLAYING', 'STOPPED'
    except Empty:
        pass
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        sub.unsubscribe()
        sub2.unsubscribe()
        event_listener.stop()
        print("Stopped monitoring")
        break

