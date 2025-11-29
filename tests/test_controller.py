"""
Tests for Playback Controller
"""

import pytest
import time
import threading
from src.controller import PlaybackController
from src.commands import Command, CommandType
from tests.mock_sonos import MockSonos


@pytest.fixture
def mock_sonos():
    """Create mock Sonos speaker"""
    return MockSonos()


@pytest.fixture
def mock_db():
    """Create mock music database"""
    return {
        '1': {
            'key': 'album1',
            'title': 'Test Album 1',
            'artist': 'Test Artist',
            'tracks': {
                '1': {
                    'song': 'Song 1',
                    'artist': 'Artist 1',
                    'length': '3:30',
                    'key': 'song1',
                    'path': ['/media/song1.mp3']
                },
                '2': {
                    'song': 'Song 2',
                    'artist': 'Artist 2',
                    'length': '4:00',
                    'key': 'song2',
                    'path': ['/media/song2.mp3']
                }
            }
        },
        '2': {
            'key': 'album2',
            'title': 'Test Album 2',
            'artist': 'Test Artist 2',
            'tracks': {
                '1': {
                    'song': 'Another Song',
                    'artist': 'Another Artist',
                    'length': '2:45',
                    'key': 'song3',
                    'path': ['/media/song3.mp3']
                }
            }
        }
    }


@pytest.fixture
def mock_db_songkey():
    """Create mock song key lookup"""
    return {
        'song1': ['1'],
        'song2': ['1'],
        'song3': ['2']
    }


@pytest.fixture
def controller(mock_sonos, mock_db, mock_db_songkey):
    """Create controller instance"""
    ctrl = PlaybackController(
        sonos=mock_sonos,
        db=mock_db,
        db_songkey=mock_db_songkey,
        mediahost="localhost",
        mediaport=54000,
        mediapath="/test"
    )
    ctrl.start()
    yield ctrl
    ctrl.stop()


class TestControllerLifecycle:
    """Test controller start/stop"""
    
    def test_controller_starts(self, controller):
        """Test controller starts successfully"""
        assert controller.running is True
        assert controller.thread is not None
        assert controller.thread.is_alive()
    
    def test_controller_stops(self, controller):
        """Test controller stops cleanly"""
        controller.stop()
        assert controller.running is False
        time.sleep(0.2)
        assert not controller.thread.is_alive()
    
    def test_double_start_warning(self, controller, caplog):
        """Test starting already-running controller"""
        controller.start()
        assert "already running" in caplog.text.lower()


class TestPlaybackCommands:
    """Test playback control commands"""
    
    def test_play_command(self, controller, mock_sonos):
        """Test play command"""
        # First add a song and start playback
        controller.command_queue.put(Command(
            CommandType.ADD_SONGS,
            data={'songs': [{'path': 'http://test/song.mp3', 'title': 'Test'}]}
        ))
        time.sleep(0.1)
        
        # Start playback with next
        controller.command_queue.put(Command(CommandType.NEXT))
        time.sleep(0.1)
        
        # Pause it
        controller.command_queue.put(Command(CommandType.PAUSE))
        time.sleep(0.1)
        assert mock_sonos.state == "PAUSED"
        
        # Now play should resume
        controller.command_queue.put(Command(CommandType.PLAY))
        time.sleep(0.1)
        
        assert mock_sonos.state == "PLAYING"
        assert mock_sonos.get_call_count('play') >= 1
    
    def test_pause_command(self, controller, mock_sonos):
        """Test pause command"""
        controller.command_queue.put(Command(CommandType.PAUSE))
        time.sleep(0.2)
        
        assert mock_sonos.state == "PAUSED"
        assert mock_sonos.get_call_count('pause') == 1
    
    def test_stop_command(self, controller, mock_sonos):
        """Test stop command"""
        controller.command_queue.put(Command(CommandType.STOP))
        time.sleep(0.2)
        
        assert mock_sonos.state == "STOPPED"
        assert mock_sonos.get_call_count('stop') == 1


class TestNextPrevious:
    """Test next/previous functionality"""
    
    def test_next_plays_first_song(self, controller, mock_sonos):
        """Test next command plays first song from queue"""
        # Add song to queue
        song = {
            'title': 'Test Song',
            'artist': 'Test Artist',
            'path': 'http://test/song.mp3',
            'album': 'Test Album'
        }
        controller.musicqueue.append(song)
        
        # Play next
        controller.command_queue.put(Command(CommandType.NEXT))
        time.sleep(0.2)
        
        # Verify song is playing
        assert mock_sonos.current_uri == 'http://test/song.mp3'
        playing = controller.get_playing()
        assert playing['title'] == 'Test Song'
        assert len(controller.get_queue()) == 0
    
    def test_next_with_empty_queue(self, controller, mock_sonos):
        """Test next with empty queue"""
        controller.command_queue.put(Command(CommandType.NEXT))
        time.sleep(0.2)
        
        # Should not crash
        assert controller.get_playing() == {}
    
    def test_repeat_mode_keeps_song_in_queue(self, controller, mock_sonos):
        """Test repeat mode re-adds song to queue"""
        controller.repeat = True
        song = {'title': 'Test', 'path': 'http://test/song.mp3'}
        controller.musicqueue.append(song)
        
        controller.command_queue.put(Command(CommandType.NEXT))
        time.sleep(0.2)
        
        # Song should still be in queue due to repeat
        assert len(controller.get_queue()) == 1
        assert controller.get_queue()[0]['title'] == 'Test'
    
    def test_prev_replays_current_song(self, controller, mock_sonos):
        """Test previous replays current song"""
        song = {'title': 'Test', 'path': 'http://test/song.mp3'}
        controller.playing = song
        
        mock_sonos.reset_call_log()
        controller.command_queue.put(Command(CommandType.PREV))
        time.sleep(0.2)
        
        assert mock_sonos.was_called_with('play_uri', 'http://test/song.mp3')


class TestQueueManagement:
    """Test queue management commands"""
    
    def test_add_album(self, controller):
        """Test adding album to queue"""
        controller.command_queue.put(Command(
            CommandType.ADD_ALBUM,
            data={'album_id': '1'}
        ))
        time.sleep(0.2)
        
        queue = controller.get_queue()
        assert len(queue) == 2
        assert queue[0]['title'] == 'Song 1'
        assert queue[1]['title'] == 'Song 2'
    
    def test_add_album_invalid_id(self, controller, caplog):
        """Test adding non-existent album"""
        controller.command_queue.put(Command(
            CommandType.ADD_ALBUM,
            data={'album_id': '999'}
        ))
        time.sleep(0.2)
        
        assert "not found" in caplog.text.lower()
        assert len(controller.get_queue()) == 0
    
    def test_add_songs(self, controller):
        """Test adding multiple songs"""
        songs = [
            {'title': 'Song A', 'path': 'http://test/a.mp3'},
            {'title': 'Song B', 'path': 'http://test/b.mp3'}
        ]
        
        controller.command_queue.put(Command(
            CommandType.ADD_SONGS,
            data={'songs': songs}
        ))
        time.sleep(0.2)
        
        queue = controller.get_queue()
        assert len(queue) == 2
        assert queue[0]['title'] == 'Song A'
    
    def test_clear_queue(self, controller):
        """Test clearing queue"""
        # Add some songs
        controller.musicqueue.extend([
            {'title': 'Song 1', 'path': 'http://test/1.mp3'},
            {'title': 'Song 2', 'path': 'http://test/2.mp3'}
        ])
        
        controller.command_queue.put(Command(CommandType.CLEAR_QUEUE))
        time.sleep(0.2)
        
        assert len(controller.get_queue()) == 0


class TestVolumeControl:
    """Test volume commands"""
    
    def test_volume_up(self, controller, mock_sonos):
        """Test volume up command"""
        mock_sonos.group.volume = 50
        
        controller.command_queue.put(Command(CommandType.VOLUME_UP))
        time.sleep(0.2)
        
        assert mock_sonos.group.volume == 51
    
    def test_volume_down(self, controller, mock_sonos):
        """Test volume down command"""
        mock_sonos.group.volume = 50
        
        controller.command_queue.put(Command(CommandType.VOLUME_DOWN))
        time.sleep(0.2)
        
        assert mock_sonos.group.volume == 49
    
    def test_set_volume(self, controller, mock_sonos):
        """Test set volume command"""
        controller.command_queue.put(Command(
            CommandType.SET_VOLUME,
            data={'volume': 75}
        ))
        time.sleep(0.2)
        
        assert mock_sonos.group.volume == 75
    
    def test_volume_bounds(self, controller, mock_sonos):
        """Test volume stays within 0-100"""
        # Test upper bound
        mock_sonos.group.volume = 100
        controller.command_queue.put(Command(CommandType.VOLUME_UP))
        time.sleep(0.2)
        assert mock_sonos.group.volume == 100
        
        # Test lower bound
        mock_sonos.group.volume = 0
        controller.command_queue.put(Command(CommandType.VOLUME_DOWN))
        time.sleep(0.2)
        assert mock_sonos.group.volume == 0


class TestSettingsToggle:
    """Test toggle commands"""
    
    def test_toggle_repeat(self, controller):
        """Test repeat toggle"""
        assert controller.repeat is False
        
        controller.command_queue.put(Command(CommandType.TOGGLE_REPEAT))
        time.sleep(0.2)
        assert controller.get_state()['repeat'] is True
        
        controller.command_queue.put(Command(CommandType.TOGGLE_REPEAT))
        time.sleep(0.2)
        assert controller.get_state()['repeat'] is False
    
    def test_toggle_shuffle(self, controller):
        """Test shuffle toggle"""
        assert controller.shuffle is False
        
        controller.command_queue.put(Command(CommandType.TOGGLE_SHUFFLE))
        time.sleep(0.2)
        assert controller.get_state()['shuffle'] is True


class TestJukeboxFunctionality:
    """Test automatic playback (jukebox mode)"""
    
    def test_track_ended_plays_next(self, controller, mock_sonos):
        """Test track ending triggers next song"""
        # Add two songs
        controller.musicqueue.extend([
            {'title': 'Song 1', 'path': 'http://test/1.mp3'},
            {'title': 'Song 2', 'path': 'http://test/2.mp3'}
        ])
        
        # Simulate track ending
        controller.command_queue.put(Command(CommandType._TRACK_ENDED))
        time.sleep(0.2)
        
        # Should auto-play next song
        assert controller.get_playing()['title'] == 'Song 1'
        assert len(controller.get_queue()) == 1
    
    def test_track_ended_with_empty_queue(self, controller):
        """Test track ending with no songs queued"""
        controller.playing = {'title': 'Last Song'}
        
        controller.command_queue.put(Command(CommandType._TRACK_ENDED))
        time.sleep(0.2)
        
        # Should stop and clear playing
        assert controller.get_playing() == {}
        assert controller.get_state()['state'] == "STOPPED"
    
    def test_auto_play_statistics(self, controller):
        """Test auto-play count is tracked"""
        controller.musicqueue.append({'title': 'Test', 'path': 'http://test/1.mp3'})
        
        controller.command_queue.put(Command(CommandType._TRACK_ENDED))
        time.sleep(0.2)
        
        stats = controller.get_stats()
        assert stats['auto_plays'] == 1


class TestThreadSafety:
    """Test thread safety of read operations"""
    
    def test_concurrent_state_reads(self, controller):
        """Test multiple threads reading state safely"""
        results = []
        
        def reader():
            for _ in range(100):
                state = controller.get_state()
                results.append(state['queue_depth'])
        
        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should complete without exceptions
        assert len(results) == 1000
    
    def test_concurrent_queue_reads(self, controller):
        """Test multiple threads reading queue safely"""
        controller.musicqueue.append({'title': 'Test'})
        
        results = []
        
        def reader():
            for _ in range(100):
                queue = controller.get_queue()
                results.append(len(queue))
        
        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 1000
        assert all(r == 1 for r in results)


class TestSSECallbacks:
    """Test SSE notification callbacks"""
    
    def test_track_changed_callback(self, controller):
        """Test track changed callback is called"""
        called = []
        
        def callback(data):
            called.append(data)
        
        controller.on_track_changed = callback
        
        # Add and play song
        controller.musicqueue.append({
            'title': 'Test Song',
            'artist': 'Test Artist',
            'path': 'http://test/song.mp3'
        })
        controller.command_queue.put(Command(CommandType.NEXT))
        time.sleep(0.2)
        
        assert len(called) == 1
        assert called[0]['title'] == 'Test Song'
        assert called[0]['artist'] == 'Test Artist'
    
    def test_queue_changed_callback(self, controller):
        """Test queue changed callback is called"""
        called = []
        
        def callback(data):
            called.append(data)
        
        controller.on_queue_changed = callback
        
        # Add songs
        controller.command_queue.put(Command(
            CommandType.ADD_SONGS,
            data={'songs': [
                {'title': 'Song 1', 'path': 'http://test/1.mp3'},
                {'title': 'Song 2', 'path': 'http://test/2.mp3'}
            ]}
        ))
        time.sleep(0.2)
        
        assert len(called) >= 1
        assert called[-1]['queuedepth'] == 2
    
    def test_state_changed_callback(self, controller):
        """Test state changed callback is called"""
        called = []
        
        def callback(data):
            called.append(data)
        
        controller.on_state_changed = callback
        
        controller.command_queue.put(Command(CommandType.TOGGLE_REPEAT))
        time.sleep(0.2)
        
        assert len(called) >= 1
        assert called[-1]['repeat'] is True


class TestStatistics:
    """Test statistics tracking"""
    
    def test_commands_processed_count(self, controller):
        """Test command processing is counted"""
        for _ in range(5):
            controller.command_queue.put(Command(CommandType.TOGGLE_REPEAT))
        
        time.sleep(0.3)
        
        stats = controller.get_stats()
        assert stats['commands_processed'] >= 5
    
    def test_songs_played_count(self, controller):
        """Test songs played is counted"""
        controller.musicqueue.extend([
            {'title': 'Song 1', 'path': 'http://test/1.mp3'},
            {'title': 'Song 2', 'path': 'http://test/2.mp3'}
        ])
        
        controller.command_queue.put(Command(CommandType.NEXT))
        time.sleep(0.2)
        controller.command_queue.put(Command(CommandType.NEXT))
        time.sleep(0.2)
        
        stats = controller.get_stats()
        assert stats['songs_played'] == 2


class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_album_id_handled(self, controller):
        """Test invalid album ID doesn't crash"""
        controller.command_queue.put(Command(
            CommandType.ADD_ALBUM,
            data={'album_id': 'invalid'}
        ))
        time.sleep(0.2)
        
        # Should not crash
        assert controller.running is True
    
    def test_command_callback_error_handled(self, controller, caplog):
        """Test errors in callbacks are handled"""
        def bad_callback():
            raise Exception("Callback error")
        
        controller.command_queue.put(Command(
            CommandType.PLAY,
            callback=bad_callback
        ))
        time.sleep(0.2)
        
        # Should handle error and continue
        assert controller.running is True
        assert "callback" in caplog.text.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
