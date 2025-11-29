"""
Mock Sonos Speaker for Testing
Simulates Sonos behavior without requiring real hardware
"""

import threading
import time
from typing import Optional, Callable, Dict, Any, List


class MockSonosEvent:
    """Mock event object for Sonos event subscriptions"""
    def __init__(self, variables: Dict[str, Any]):
        self.variables = variables


class MockSonosSubscription:
    """Mock subscription for Sonos events"""
    def __init__(self, parent):
        self.parent = parent
        self.callback: Optional[Callable] = None
        self.auto_renew = False
        self.active = True
    
    def unsubscribe(self):
        """Unsubscribe from events"""
        self.active = False
        if self in self.parent.subscriptions:
            self.parent.subscriptions.remove(self)


class MockAVTransport:
    """Mock AVTransport service for event subscriptions"""
    def __init__(self, parent):
        self.parent = parent
    
    def subscribe(self, auto_renew=False, event_queue=None):
        """Subscribe to transport events"""
        subscription = MockSonosSubscription(self.parent)
        subscription.auto_renew = auto_renew
        self.parent.subscriptions.append(subscription)
        return subscription


class MockSonosGroup:
    """Mock Sonos group"""
    def __init__(self, sonos):
        self.sonos = sonos
        self._volume = 50
        self.coordinator = sonos
        self.members = [sonos]
    
    @property
    def volume(self):
        return self._volume
    
    @volume.setter
    def volume(self, value):
        self._volume = max(0, min(100, value))


class MockSonos:
    """
    Mock Sonos speaker for testing.
    Simulates play_uri, stop, pause, volume, and event subscription.
    """
    
    def __init__(self, ip_address="192.168.1.100", player_name="Test Speaker"):
        self.ip_address = ip_address
        self.player_name = player_name
        self.household_id = "test_household"
        self.uid = "test_uid"
        
        # Playback state
        self.state = "STOPPED"
        self.current_uri: Optional[str] = None
        self.current_track_info = {
            'title': '',
            'artist': '',
            'album': '',
            'position': '0:00:00',
            'duration': '0:00:00',
            'album_art': ''
        }
        
        # Group and volume
        self.group = MockSonosGroup(self)
        self._volume = 50
        
        # Event system
        self.avTransport = MockAVTransport(self)
        self.subscriptions: List[MockSonosSubscription] = []
        
        # Call tracking for assertions
        self.call_log: List[tuple] = []
        
        # Simulate async playback
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_playback = threading.Event()
    
    @property
    def volume(self):
        return self._volume
    
    @volume.setter
    def volume(self, value):
        self._volume = max(0, min(100, value))
        self.call_log.append(('set_volume', value))
    
    def play_uri(self, uri: str):
        """Play a URI"""
        self.call_log.append(('play_uri', uri))
        self.current_uri = uri
        self.state = "PLAYING"
        
        # Extract track info from URI if possible
        if uri:
            filename = uri.split('/')[-1]
            self.current_track_info['title'] = filename
        
        # Emit state change event
        self._emit_event({'transport_state': 'PLAYING'})
        
        # Simulate playback duration (short for testing)
        self._start_playback_simulation(duration=0.5)
    
    def play(self):
        """Resume playback"""
        self.call_log.append(('play',))
        if self.current_uri:
            self.state = "PLAYING"
            self._emit_event({'transport_state': 'PLAYING'})
    
    def pause(self):
        """Pause playback"""
        self.call_log.append(('pause',))
        self.state = "PAUSED"
        self._stop_playback.set()
        self._emit_event({'transport_state': 'PAUSED'})
    
    def stop(self):
        """Stop playback"""
        self.call_log.append(('stop',))
        self.state = "STOPPED"
        self._stop_playback.set()
        self._emit_event({'transport_state': 'STOPPED'})
    
    def next(self):
        """Skip to next track"""
        self.call_log.append(('next',))
    
    def previous(self):
        """Go to previous track"""
        self.call_log.append(('previous',))
    
    def get_current_transport_info(self):
        """Get transport state"""
        self.call_log.append(('get_current_transport_info',))
        return {
            'current_transport_state': self.state,
            'current_transport_status': 'OK'
        }
    
    def get_current_track_info(self):
        """Get current track information"""
        self.call_log.append(('get_current_track_info',))
        return self.current_track_info.copy()
    
    def clear_queue(self):
        """Clear Sonos queue"""
        self.call_log.append(('clear_queue',))
    
    def _start_playback_simulation(self, duration: float = 0.5):
        """Simulate playback for testing (track ends after duration)"""
        if self._playback_thread and self._playback_thread.is_alive():
            self._stop_playback.set()
            self._playback_thread.join(timeout=1)
        
        self._stop_playback.clear()
        self._playback_thread = threading.Thread(
            target=self._simulate_playback,
            args=(duration,),
            daemon=True
        )
        self._playback_thread.start()
    
    def _simulate_playback(self, duration: float):
        """Simulate track playback and emit STOPPED event when done"""
        if self._stop_playback.wait(timeout=duration):
            # Stopped early
            return
        
        # Track finished naturally
        if self.state == "PLAYING":
            self.state = "STOPPED"
            self._emit_event({'transport_state': 'STOPPED'})
    
    def _emit_event(self, variables: Dict[str, Any]):
        """Emit event to all subscribers"""
        event = MockSonosEvent(variables)
        for subscription in self.subscriptions:
            if subscription.active and subscription.callback:
                try:
                    subscription.callback(event)
                except Exception as e:
                    print(f"Error in event callback: {e}")
    
    def emit_event_external(self, variables: Dict[str, Any]):
        """Manually emit event (for testing)"""
        self._emit_event(variables)
    
    def reset_call_log(self):
        """Clear call log"""
        self.call_log.clear()
    
    def get_call_count(self, method_name: str) -> int:
        """Count how many times a method was called"""
        return sum(1 for call in self.call_log if call[0] == method_name)
    
    def was_called_with(self, method_name: str, *args) -> bool:
        """Check if method was called with specific arguments"""
        target = (method_name,) + args
        return target in self.call_log


def create_mock_sonos(**kwargs) -> MockSonos:
    """Factory function to create mock Sonos with custom properties"""
    return MockSonos(**kwargs)
