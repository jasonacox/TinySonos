"""
Adapter Layer for TinySonos
Provides backward compatibility between old global-variable architecture
and new command-queue controller architecture.
"""

import logging
from typing import List, Dict, Optional
from src.commands import Command, CommandType, create_command
from src.controller import PlaybackController

log = logging.getLogger(__name__)


class ControllerAdapter:
    """
    Adapter that provides the old global-variable interface
    but delegates to the new PlaybackController.
    
    This allows existing server.py code to work without modification
    while using the new architecture under the hood.
    """
    
    def __init__(self, controller: PlaybackController):
        """
        Initialize adapter with controller.
        
        Args:
            controller: PlaybackController instance
        """
        self.controller = controller
        self._legacy_stop_flag = False
    
    # ========================================================================
    # PROPERTIES - Mimic old globals with backward compatibility
    # ========================================================================
    
    @property
    def musicqueue(self) -> List[Dict]:
        """
        Read-only access to queue.
        For compatibility with code that reads musicqueue.
        """
        return self.controller.get_queue()
    
    @musicqueue.setter
    def musicqueue(self, value: List[Dict]):
        """
        Handle direct queue assignment (used in old code).
        Clear queue and add new songs.
        """
        log.warning("Direct musicqueue assignment - using compatibility mode")
        self.controller.command_queue.put(Command(CommandType.CLEAR_QUEUE))
        if value:
            self.controller.command_queue.put(Command(
                CommandType.ADD_SONGS,
                data={'songs': value}
            ))
    
    @property
    def playing(self) -> Dict:
        """Read-only access to currently playing song"""
        return self.controller.get_playing()
    
    @playing.setter
    def playing(self, value: Dict):
        """
        Handle direct playing assignment.
        In new architecture, this is managed by controller.
        """
        log.debug(f"Playing set to: {value.get('title', 'Unknown')}")
        # Controller manages this, but we can update internal state for reads
        self.controller.playing = value
    
    @property
    def state(self) -> str:
        """Read-only access to state"""
        return self.controller.get_state()['state']
    
    @property
    def repeat(self) -> bool:
        """Get repeat mode"""
        return self.controller.repeat
    
    @repeat.setter
    def repeat(self, value: bool):
        """Set repeat mode directly (for old code compatibility)"""
        self.controller.repeat = value
    
    @property
    def shuffle(self) -> bool:
        """Get shuffle mode"""
        return self.controller.shuffle
    
    @shuffle.setter
    def shuffle(self, value: bool):
        """Set shuffle mode directly (for old code compatibility)"""
        self.controller.shuffle = value
    
    @property
    def stop(self) -> bool:
        """
        Legacy stop flag for compatibility.
        In new architecture, this is not needed, but old code checks it.
        """
        return self._legacy_stop_flag
    
    @stop.setter
    def stop(self, value: bool):
        """
        Set stop flag - for compatibility only.
        New architecture doesn't use this flag.
        """
        self._legacy_stop_flag = value
    
    # ========================================================================
    # COMMAND METHODS - Enqueue commands instead of direct operations
    # ========================================================================
    
    def enqueue_next(self):
        """Enqueue next command"""
        self.controller.command_queue.put(Command(CommandType.NEXT))
    
    def enqueue_prev(self):
        """Enqueue prev command"""
        self.controller.command_queue.put(Command(CommandType.PREV))
    
    def enqueue_play(self):
        """Enqueue play command"""
        self.controller.command_queue.put(Command(CommandType.PLAY))
    
    def enqueue_pause(self):
        """Enqueue pause command"""
        self.controller.command_queue.put(Command(CommandType.PAUSE))
    
    def enqueue_stop(self):
        """Enqueue stop command"""
        self.controller.command_queue.put(Command(CommandType.STOP))
    
    def enqueue_volume_up(self):
        """Enqueue volume up command"""
        self.controller.command_queue.put(Command(CommandType.VOLUME_UP))
    
    def enqueue_volume_down(self):
        """Enqueue volume down command"""
        self.controller.command_queue.put(Command(CommandType.VOLUME_DOWN))
    
    def enqueue_set_volume(self, volume: int):
        """Enqueue set volume command"""
        self.controller.command_queue.put(create_command(
            CommandType.SET_VOLUME,
            volume=volume
        ))
    
    def enqueue_toggle_repeat(self):
        """Enqueue toggle repeat command"""
        self.controller.command_queue.put(Command(CommandType.TOGGLE_REPEAT))
    
    def enqueue_toggle_shuffle(self):
        """Enqueue toggle shuffle command"""
        self.controller.command_queue.put(Command(CommandType.TOGGLE_SHUFFLE))
    
    def enqueue_add_album(self, album_id: str):
        """Enqueue add album command"""
        self.controller.command_queue.put(create_command(
            CommandType.ADD_ALBUM,
            album_id=album_id
        ))
    
    def enqueue_add_song(self, song_data: Dict):
        """Enqueue add song command"""
        self.controller.command_queue.put(create_command(
            CommandType.ADD_SONG,
            **song_data
        ))
    
    def enqueue_add_songs(self, songs: List[Dict]):
        """Enqueue add multiple songs command"""
        self.controller.command_queue.put(create_command(
            CommandType.ADD_SONGS,
            songs=songs
        ))
    
    def enqueue_clear_queue(self):
        """Enqueue clear queue command"""
        self.controller.command_queue.put(Command(CommandType.CLEAR_QUEUE))
    
    def enqueue_switch_zone(self, zone_ip: str):
        """Enqueue switch zone command"""
        self.controller.command_queue.put(create_command(
            CommandType.SWITCH_ZONE,
            zone_ip=zone_ip
        ))
    
    # ========================================================================
    # HELPER METHODS - For common patterns in old code
    # ========================================================================
    
    def append_to_queue(self, song: Dict):
        """
        Append single song to queue.
        Compatibility method for: musicqueue.append(song)
        """
        self.enqueue_add_song(song)
    
    def extend_queue(self, songs: List[Dict]):
        """
        Extend queue with multiple songs.
        Compatibility method for: musicqueue.extend(songs)
        """
        self.enqueue_add_songs(songs)
    
    def pop_from_queue(self) -> Optional[Dict]:
        """
        Pop song from queue.
        WARNING: This breaks the command queue pattern!
        Only for legacy compatibility during migration.
        """
        log.warning("Legacy pop_from_queue called - should use commands instead")
        queue = self.controller.get_queue()
        if queue:
            song = queue[0]
            # Remove from actual queue
            if self.controller.musicqueue:
                self.controller.musicqueue.pop(0)
            return song
        return None
    
    def clear_queue(self):
        """
        Clear the queue.
        Compatibility method for: musicqueue.clear()
        """
        self.enqueue_clear_queue()
    
    # ========================================================================
    # DIRECT ACCESS METHODS - For reading state (thread-safe)
    # ========================================================================
    
    def get_queue_length(self) -> int:
        """Get queue length"""
        return len(self.controller.get_queue())
    
    def get_queue_copy(self) -> List[Dict]:
        """Get copy of queue"""
        return self.controller.get_queue()
    
    def get_playing_copy(self) -> Dict:
        """Get copy of playing song"""
        return self.controller.get_playing()
    
    def get_full_state(self) -> Dict:
        """Get complete state snapshot"""
        return self.controller.get_state()
    
    def get_statistics(self) -> Dict:
        """Get controller statistics"""
        return self.controller.get_stats()


def create_adapter(controller: PlaybackController) -> ControllerAdapter:
    """
    Factory function to create adapter.
    
    Args:
        controller: PlaybackController instance
        
    Returns:
        ControllerAdapter instance
    """
    return ControllerAdapter(controller)
