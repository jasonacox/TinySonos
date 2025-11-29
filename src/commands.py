"""
Command System for TinySonos
Defines command types and command queue for thread-safe operation
"""

import queue
import threading
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Dict


class CommandType(Enum):
    """Types of commands that can be sent to the controller"""
    
    # Playback control
    PLAY = "play"
    PAUSE = "pause"
    STOP = "stop"
    NEXT = "next"
    PREV = "prev"
    
    # Queue management
    ADD_SONG = "add_song"
    ADD_ALBUM = "add_album"
    ADD_PLAYLIST = "add_playlist"
    ADD_SONGS = "add_songs"
    CLEAR_QUEUE = "clear_queue"
    
    # Settings
    SET_VOLUME = "set_volume"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    TOGGLE_REPEAT = "toggle_repeat"
    TOGGLE_SHUFFLE = "toggle_shuffle"
    
    # Zone management
    SWITCH_ZONE = "switch_zone"
    
    # Internal commands (prefixed with _)
    _TRACK_ENDED = "_track_ended"
    _UPDATE_STATE = "_update_state"
    _WATCHDOG_CHECK = "_watchdog_check"


@dataclass
class Command:
    """
    Represents a command to be executed by the controller.
    Commands are immutable and contain all necessary data.
    """
    type: CommandType
    data: Optional[Dict[str, Any]] = None
    callback: Optional[Callable] = None
    timestamp: float = field(default_factory=time.time)
    
    def __repr__(self):
        data_str = f", data={self.data}" if self.data else ""
        return f"Command({self.type.value}{data_str})"


class CommandQueue:
    """
    Thread-safe command queue with statistics tracking.
    Wraps Python's queue.Queue with additional features.
    """
    
    def __init__(self, maxsize: int = 0):
        """
        Initialize command queue.
        
        Args:
            maxsize: Maximum queue size (0 = unlimited)
        """
        self._queue = queue.Queue(maxsize=maxsize)
        self._stats = {
            'total_commands': 0,
            'pending': 0,
            'processed': 0,
            'errors': 0
        }
        self._lock = threading.Lock()
    
    def put(self, command: Command, block: bool = True, timeout: Optional[float] = None):
        """
        Add command to queue.
        
        Args:
            command: Command to enqueue
            block: Block if queue is full
            timeout: Timeout for blocking
        
        Raises:
            queue.Full: If queue is full and not blocking
        """
        self._queue.put(command, block=block, timeout=timeout)
        with self._lock:
            self._stats['total_commands'] += 1
            self._stats['pending'] += 1
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Command:
        """
        Get next command from queue.
        
        Args:
            block: Block if queue is empty
            timeout: Timeout for blocking
        
        Returns:
            Next command in queue
        
        Raises:
            queue.Empty: If queue is empty and not blocking
        """
        cmd = self._queue.get(block=block, timeout=timeout)
        with self._lock:
            self._stats['pending'] -= 1
        return cmd
    
    def qsize(self) -> int:
        """Get approximate queue size"""
        return self._queue.qsize()
    
    def empty(self) -> bool:
        """Check if queue is empty"""
        return self._queue.empty()
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with queue statistics
        """
        with self._lock:
            return self._stats.copy()
    
    def mark_processed(self):
        """Mark a command as successfully processed"""
        with self._lock:
            self._stats['processed'] += 1
    
    def mark_error(self):
        """Mark a command as having an error"""
        with self._lock:
            self._stats['errors'] += 1
    
    def reset_stats(self):
        """Reset statistics counters"""
        with self._lock:
            self._stats = {
                'total_commands': 0,
                'pending': self._stats['pending'],  # Keep pending count
                'processed': 0,
                'errors': 0
            }


def create_command(cmd_type: CommandType, **kwargs) -> Command:
    """
    Factory function to create commands with data.
    
    Args:
        cmd_type: Type of command
        **kwargs: Data to include in command
    
    Returns:
        Command instance
    
    Example:
        cmd = create_command(CommandType.ADD_ALBUM, album_id=123)
    """
    data = kwargs if kwargs else None
    return Command(type=cmd_type, data=data)
