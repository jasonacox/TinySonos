"""
Playback Controller for TinySonos
Single-threaded controller that manages all playback state and operations
"""

import threading
import logging
import queue as queue_module
import os
import time
import requests
from typing import Optional, Dict, List, Callable, Any

from .commands import Command, CommandType, CommandQueue

log = logging.getLogger(__name__)


class PlaybackController:
    """
    Single-threaded controller that manages all playback state.
    All state mutations happen in the controller thread only.
    
    This is the core of the jukebox functionality - it ensures continuous
    playback by automatically queuing the next song when one ends.
    """
    
    def __init__(self, sonos, db, db_songkey, mediahost, mediaport, mediapath):
        """
        Initialize the playback controller.
        
        Args:
            sonos: Sonos speaker instance
            db: Music database
            db_songkey: Song key lookup dictionary
            mediahost: Media server hostname
            mediaport: Media server port
            mediapath: Path to media files
        """
        # Dependencies
        self.sonos = sonos
        self.db = db
        self.db_songkey = db_songkey
        self.mediahost = mediahost
        self.mediaport = mediaport
        self.mediapath = mediapath
        
        # State (owned by controller thread - DO NOT ACCESS FROM OTHER THREADS)
        self.musicqueue: List[Dict] = []
        self.playing: Dict = {}
        self.state: str = "STOPPED"
        self.repeat: bool = False
        self.shuffle: bool = False
        
        # Thread management
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.command_queue = CommandQueue()
        
        # Read lock (for thread-safe reads from API handlers)
        self._read_lock = threading.RLock()
        
        # Statistics
        self.stats = {
            'commands_processed': 0,
            'errors': 0,
            'songs_played': 0,
            'auto_plays': 0  # Songs played automatically by jukebox
        }
        
        # Callbacks for SSE broadcasting (set by server.py)
        self.on_track_changed: Optional[Callable] = None
        self.on_queue_changed: Optional[Callable] = None
        self.on_state_changed: Optional[Callable] = None
        self.on_volume_changed: Optional[Callable] = None
    
    def start(self):
        """Start the controller thread"""
        if self.running:
            log.warning("Controller already running")
            return
        
        self.running = True
        self.thread = threading.Thread(
            target=self._run,
            name="PlaybackController",
            daemon=True
        )
        self.thread.start()
        
        # Start monitoring thread to auto-play next song when current ends
        self.monitor_thread = threading.Thread(
            target=self._monitor_playback,
            name="PlaybackMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        
        log.info("PlaybackController: Started")
    
    def stop(self):
        """Stop the controller thread gracefully"""
        if not self.running:
            return
        
        log.info("PlaybackController: Stopping...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                log.warning("Controller thread did not stop cleanly")
        
        log.info("PlaybackController: Stopped")
    
    def _run(self):
        """
        Main controller loop - processes commands.
        This is the ONLY place where state is modified.
        """
        while self.running:
            try:
                # Get next command (with timeout to check running flag)
                try:
                    cmd = self.command_queue.get(timeout=0.1)
                    self._process_command(cmd)
                except queue_module.Empty:
                    continue
                    
            except Exception as e:
                log.error(f"Controller error: {e}", exc_info=True)
                self.stats['errors'] += 1
    
    def _process_command(self, cmd: Command):
        """
        Process a single command (runs in controller thread only).
        
        Args:
            cmd: Command to process
        """
        log.debug(f"Processing command: {cmd.type.value}")
        
        try:
            # Dispatch to appropriate handler
            if cmd.type == CommandType.NEXT:
                self._handle_next()
            elif cmd.type == CommandType.PREV:
                self._handle_prev()
            elif cmd.type == CommandType.PLAY:
                self._handle_play()
            elif cmd.type == CommandType.PAUSE:
                self._handle_pause()
            elif cmd.type == CommandType.STOP:
                self._handle_stop()
            elif cmd.type == CommandType.ADD_ALBUM:
                self._handle_add_album(cmd.data)
            elif cmd.type == CommandType.ADD_SONG:
                self._handle_add_song(cmd.data)
            elif cmd.type == CommandType.ADD_SONGS:
                self._handle_add_songs(cmd.data)
            elif cmd.type == CommandType.ADD_PLAYLIST:
                self._handle_add_playlist(cmd.data)
            elif cmd.type == CommandType.CLEAR_QUEUE:
                self._handle_clear_queue()
            elif cmd.type == CommandType.SET_VOLUME:
                self._handle_set_volume(cmd.data)
            elif cmd.type == CommandType.VOLUME_UP:
                self._handle_volume_up()
            elif cmd.type == CommandType.VOLUME_DOWN:
                self._handle_volume_down()
            elif cmd.type == CommandType.TOGGLE_REPEAT:
                self._handle_toggle_repeat()
            elif cmd.type == CommandType.TOGGLE_SHUFFLE:
                self._handle_toggle_shuffle()
            elif cmd.type == CommandType.SWITCH_ZONE:
                self._handle_switch_zone(cmd.data)
            elif cmd.type == CommandType._TRACK_ENDED:
                self._handle_track_ended()
            elif cmd.type == CommandType._UPDATE_STATE:
                self._handle_update_state(cmd.data)
            else:
                log.warning(f"Unknown command type: {cmd.type}")
            
            self.stats['commands_processed'] += 1
            self.command_queue.mark_processed()
            
            # Execute callback if provided
            if cmd.callback:
                try:
                    cmd.callback()
                except Exception as e:
                    log.error(f"Error in command callback: {e}")
                    
        except Exception as e:
            log.error(f"Error processing command {cmd.type}: {e}", exc_info=True)
            self.stats['errors'] += 1
            self.command_queue.mark_error()
    
    # ========================================================================
    # PLAYBACK CONTROL HANDLERS
    # ========================================================================
    
    def _handle_next(self):
        """
        Play next song from queue.
        This is the core jukebox functionality.
        """
        if not self.musicqueue:
            log.info("Next: Queue empty")
            self.playing = {}
            self._notify_track_changed()
            return
        
        # Pop next song
        self.playing = self.musicqueue.pop(0)
        if self.repeat:
            self.musicqueue.append(self.playing)
        
        # Play it
        try:
            # Stop current playback first to ensure clean transition
            try:
                self.sonos.stop()
            except:
                pass
            
            self.sonos.play_uri(self.playing['path'])
            self.state = "PLAYING"
            self.stats['songs_played'] += 1
            
            # Notify clients immediately
            self._notify_track_changed()
            self._notify_queue_changed()
            
            log.info(f"Now playing: {self.playing.get('title', 'Unknown')}")
        except Exception as e:
            log.error(f"Error playing song: {e}")
            # Try next song if current one failed
            if self.musicqueue:
                self._handle_next()
    
    def _handle_prev(self):
        """Replay current song or go to previous"""
        if not self.playing:
            log.info("Prev: Nothing playing")
            return
        
        try:
            # Replay current song
            self.sonos.play_uri(self.playing['path'])
            self.state = "PLAYING"
            self._notify_track_changed()
        except Exception as e:
            log.error(f"Error replaying song: {e}")
    
    def _handle_play(self):
        """Resume playback"""
        try:
            self.sonos.play()
            self.state = "PLAYING"
            self._notify_state_changed()
        except Exception as e:
            log.error(f"Error resuming playback: {e}")
    
    def _handle_pause(self):
        """Pause playback"""
        try:
            self.sonos.pause()
            self.state = "PAUSED"
            self._notify_state_changed()
        except Exception as e:
            log.error(f"Error pausing playback: {e}")
    
    def _handle_stop(self):
        """Stop playback"""
        try:
            self.sonos.stop()
            self.state = "STOPPED"
            self._notify_state_changed()
        except Exception as e:
            log.error(f"Error stopping playback: {e}")
    
    def _monitor_playback(self):
        """
        Monitor Sonos playback state and auto-play next song when current ends.
        This is CRITICAL for jukebox functionality - keeps music playing continuously.
        Runs in separate thread to avoid blocking command processing.
        
        HYPER-AGGRESSIVE MODE: If we have songs in queue and nothing is playing from us,
        we take over immediately - stopping any external sources (Alexa, Apple Music, etc).
        """
        last_state = None
        
        while self.running:
            try:
                # AGGRESSIVE: If we have songs in queue, we take control
                if self.musicqueue:
                    try:
                        # Get current Sonos state
                        transport_info = self.sonos.get_current_transport_info()
                        current_state = transport_info['current_transport_state']
                        
                        # Check if we're managing the current playback
                        # If queue has songs but we're not playing, TAKE OVER
                        if not self.playing and current_state != "PLAYING" and self.state == "PLAYING":
                            # Queue has songs, nothing playing, we should be playing - START!
                            log.info("Playback monitor: Queue has songs, taking control and starting playback")
                            self.command_queue.put(Command(CommandType._TRACK_ENDED))
                        elif not self.playing and current_state == "PLAYING":
                            # Something else is playing (Alexa, Apple Music, etc) but we have queue
                            # TAKE OVER - stop external source and play our music
                            log.info("Playback monitor: External source playing but we have queue - TAKING OVER")
                            try:
                                self.sonos.stop()
                            except:
                                pass
                            # Start our music
                            self.command_queue.put(Command(CommandType._TRACK_ENDED))
                        elif last_state == "PLAYING" and current_state != "PLAYING":
                            # Our song ended, auto-play next (respect user stop/pause)
                            if self.state == "PLAYING":
                                log.info("Playback monitor: Song ended, queuing next")
                                self.command_queue.put(Command(CommandType._TRACK_ENDED))
                            else:
                                log.info(f"Playback monitor: Song ended but controller state is {self.state}, respecting user command")
                        
                        last_state = current_state
                        
                    except Exception as e:
                        log.debug(f"Monitor: Error checking Sonos state: {e}")
                
                # Check every 0.5 seconds (match original jukebox aggressive polling)
                time.sleep(0.5)
                
            except Exception as e:
                log.error(f"Playback monitor error: {e}")
                time.sleep(5)  # Longer sleep on error
        
        log.info("Playback monitor: Stopped")
    
    def _handle_track_ended(self):
        """
        Handle track ending - CRITICAL JUKEBOX FUNCTION.
        Immediately plays next song to ensure continuous music.
        This handles Sonos instability/flakiness.
        
        IMPORTANT: Only auto-plays if controller state is PLAYING.
        Respects user-initiated stop/pause commands.
        """
        # Only auto-play if we're supposed to be playing (respect user stop/pause)
        if self.state != "PLAYING":
            log.info(f"Track ended but state is {self.state}, not auto-playing (user requested stop/pause)")
            return
        
        if self.musicqueue:
            log.debug("Track ended, auto-playing next song")
            self.stats['auto_plays'] += 1
            self._handle_next()
        else:
            log.debug("Track ended, queue empty")
            self.state = "STOPPED"
            self.playing = {}
            self._notify_state_changed()
            self._notify_track_changed()
    
    def _handle_update_state(self, data: Dict):
        """Update state from external event"""
        if data and 'state' in data:
            self.state = data['state']
            self._notify_state_changed()
    
    # ========================================================================
    # QUEUE MANAGEMENT HANDLERS
    # ========================================================================
    
    def _handle_add_album(self, data: Dict):
        """Add album to queue"""
        album_id = data.get('album_id')
        if not album_id or str(album_id) not in self.db:
            log.warning(f"Album {album_id} not found in database")
            return
        
        songs = self._load_album_songs(album_id)
        self.musicqueue.extend(songs)
        self._notify_queue_changed()
        log.info(f"Added {len(songs)} songs from album {album_id}")
    
    def _handle_add_song(self, data: Dict):
        """Add single song to queue"""
        song = self._build_song_from_data(data)
        if song:
            self.musicqueue.append(song)
            self._notify_queue_changed()
            log.info(f"Added song: {song.get('title', 'Unknown')}")
    
    def _handle_add_songs(self, data: Dict):
        """Add multiple songs to queue"""
        songs = data.get('songs', [])
        if songs:
            was_empty = len(self.musicqueue) == 0 and not self.playing
            self.musicqueue.extend(songs)
            self._notify_queue_changed()
            log.info(f"Added {len(songs)} songs to queue")
            
            # Auto-start playback if queue was empty and nothing playing
            if was_empty and self.state != "PLAYING":
                log.info("Queue was empty, auto-starting playback")
                self._handle_next()
    
    def _handle_add_playlist(self, data: Dict):
        """Add playlist (m3u) to queue"""
        songs = data.get('songs', [])
        if songs:
            was_empty = len(self.musicqueue) == 0 and not self.playing
            self.musicqueue.extend(songs)
            self._notify_queue_changed()
            log.info(f"Added playlist with {len(songs)} songs")
            
            # Auto-start playback if queue was empty and nothing playing
            if was_empty and self.state != "PLAYING":
                log.info("Queue was empty, auto-starting playback")
                self._handle_next()
    
    def _handle_clear_queue(self):
        """Clear the music queue"""
        count = len(self.musicqueue)
        self.musicqueue.clear()
        self._notify_queue_changed()
        log.info(f"Cleared queue ({count} songs removed)")
    
    # ========================================================================
    # VOLUME HANDLERS
    # ========================================================================
    
    def _handle_set_volume(self, data: Dict):
        """Set volume to specific level"""
        volume = data.get('volume')
        if volume is not None:
            try:
                self.sonos.group.volume = int(volume)
                self._notify_volume_changed()
            except Exception as e:
                log.error(f"Error setting volume: {e}")
    
    def _handle_volume_up(self):
        """Increase volume by 1"""
        try:
            current = self.sonos.group.volume
            self.sonos.group.volume = min(100, current + 1)
            self._notify_volume_changed()
        except Exception as e:
            log.error(f"Error increasing volume: {e}")
    
    def _handle_volume_down(self):
        """Decrease volume by 1"""
        try:
            current = self.sonos.group.volume
            self.sonos.group.volume = max(0, current - 1)
            self._notify_volume_changed()
        except Exception as e:
            log.error(f"Error decreasing volume: {e}")
    
    # ========================================================================
    # SETTINGS HANDLERS
    # ========================================================================
    
    def _handle_toggle_repeat(self):
        """Toggle repeat mode"""
        self.repeat = not self.repeat
        self._notify_state_changed()
        log.info(f"Repeat: {'ON' if self.repeat else 'OFF'}")
    
    def _handle_toggle_shuffle(self):
        """Toggle shuffle mode"""
        self.shuffle = not self.shuffle
        self._notify_state_changed()
        log.info(f"Shuffle: {'ON' if self.shuffle else 'OFF'}")
    
    def _handle_switch_zone(self, data: Dict):
        """Switch to different Sonos zone"""
        zone_ip = data.get('zone_ip')
        if zone_ip:
            try:
                import soco
                self.sonos = soco.SoCo(zone_ip).group.coordinator
                log.info(f"Switched to zone: {zone_ip}")
            except Exception as e:
                log.error(f"Error switching zone: {e}")
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _load_album_songs(self, album_id: str) -> List[Dict]:
        """
        Load all songs from an album.
        
        Args:
            album_id: Album ID in database
            
        Returns:
            List of song dictionaries
        """
        songs = []
        album = self.db[str(album_id)]
        akey = album.get("key")
        
        for item in album.get("tracks", {}).values():
            song = {
                'title': item.get("song", "Unknown"),
                'artist': item.get('artist', "Unknown"),
                'length': item.get('length', "0:00"),
                'album': album.get('title', "Unknown"),
                'albumartist': album.get('artist', "Unknown"),
                'path': f"http://{self.mediahost}:{self.mediaport}{requests.utils.quote(item['path'][0])}",
                'akey': akey,
                'skey': item.get("key")
            }
            
            # Add album art if available
            if akey and os.path.isfile(f"{self.mediapath}/album-art/{akey}.png"):
                song['album_art'] = f"http://{self.mediahost}:{self.mediaport}/album-art/{akey}.png"
            else:
                song['album_art'] = None
            
            # Add duration if available
            if 'length' in item:
                song['duration'] = item['length']
            
            songs.append(song)
        
        return songs
    
    def _build_song_from_data(self, data: Dict) -> Optional[Dict]:
        """
        Build song dictionary from command data.
        
        Args:
            data: Song data from command
            
        Returns:
            Song dictionary or None if invalid
        """
        # Implementation depends on data format
        # This is a placeholder that can be expanded
        if 'path' in data:
            return data
        
        # Try to load from db using song key
        if 'skey' in data and data['skey'] in self.db_songkey:
            album_id = self.db_songkey[data['skey']][0]
            album_tracks = self.db[str(album_id)]['tracks']
            for track in album_tracks.values():
                if track.get('key') == data['skey']:
                    return self._build_song_from_track(track, album_id)
        
        return None
    
    def _build_song_from_track(self, track: Dict, album_id: str) -> Dict:
        """Build song dict from track and album info"""
        song = {
            'title': track.get('song', 'Unknown'),
            'artist': track.get('artist', 'Unknown'),
            'length': track.get('length', '0:00'),
            'album': self.db[str(album_id)].get('title', 'Unknown'),
            'path': f"http://{self.mediahost}:{self.mediaport}/{requests.utils.quote(track['path'][0])}",
            'akey': self.db[str(album_id)].get('key'),
            'skey': track.get('key')
        }
        
        akey = song['akey']
        if akey and os.path.isfile(f"{self.mediapath}/album-art/{akey}.png"):
            song['album_art'] = f"http://{self.mediahost}:{self.mediaport}/album-art/{akey}.png"
        else:
            song['album_art'] = None
        
        return song
    
    # ========================================================================
    # SSE NOTIFICATION METHODS
    # ========================================================================
    
    def _notify_track_changed(self):
        """Notify clients of track change via SSE"""
        if self.on_track_changed:
            try:
                self.on_track_changed({
                    'title': self.playing.get('title', ''),
                    'artist': self.playing.get('artist', ''),
                    'album': self.playing.get('album', ''),
                    'position': '0:00:00',
                    'duration': self.playing.get('duration', '0:00:00'),
                    'album_art': self.playing.get('album_art', '')
                })
            except Exception as e:
                log.error(f"Error in track_changed callback: {e}")
    
    def _notify_queue_changed(self):
        """Notify clients of queue change via SSE"""
        if self.on_queue_changed:
            try:
                self.on_queue_changed({'queuedepth': len(self.musicqueue)})
            except Exception as e:
                log.error(f"Error in queue_changed callback: {e}")
    
    def _notify_state_changed(self):
        """Notify clients of state change via SSE"""
        if self.on_state_changed:
            try:
                self.on_state_changed({
                    'state': self.state,
                    'repeat': self.repeat,
                    'shuffle': self.shuffle
                })
            except Exception as e:
                log.error(f"Error in state_changed callback: {e}")
    
    def _notify_volume_changed(self):
        """Notify clients of volume change via SSE"""
        if self.on_volume_changed:
            try:
                volume = self.sonos.group.volume
                self.on_volume_changed({'volume': volume})
            except Exception as e:
                log.error(f"Error in volume_changed callback: {e}")
    
    # ========================================================================
    # THREAD-SAFE READ METHODS (for API handlers)
    # ========================================================================
    
    def get_state(self) -> Dict:
        """
        Get current state snapshot (thread-safe).
        
        Returns:
            Dictionary with current state
        """
        with self._read_lock:
            return {
                'playing': self.playing.copy() if self.playing else {},
                'queue_depth': len(self.musicqueue),
                'state': self.state,
                'repeat': self.repeat,
                'shuffle': self.shuffle
            }
    
    def get_queue(self) -> List[Dict]:
        """
        Get queue snapshot (thread-safe).
        
        Returns:
            Copy of music queue
        """
        with self._read_lock:
            return self.musicqueue.copy()
    
    def get_playing(self) -> Dict:
        """
        Get currently playing song (thread-safe).
        
        Returns:
            Copy of playing dictionary
        """
        with self._read_lock:
            return self.playing.copy() if self.playing else {}
    
    def get_stats(self) -> Dict:
        """
        Get controller statistics (thread-safe).
        
        Returns:
            Dictionary with statistics
        """
        with self._read_lock:
            stats = self.stats.copy()
            stats['queue_stats'] = self.command_queue.get_stats()
            return stats
