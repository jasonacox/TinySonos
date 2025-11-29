"""
Tests for Command System
"""

import pytest
import time
import threading
from src.commands import Command, CommandType, CommandQueue, create_command


class TestCommand:
    """Test Command class"""
    
    def test_command_creation(self):
        """Test basic command creation"""
        cmd = Command(CommandType.NEXT)
        assert cmd.type == CommandType.NEXT
        assert cmd.data is None
        assert cmd.callback is None
        assert cmd.timestamp > 0
    
    def test_command_with_data(self):
        """Test command with data"""
        cmd = Command(CommandType.ADD_ALBUM, data={'album_id': 123})
        assert cmd.type == CommandType.ADD_ALBUM
        assert cmd.data['album_id'] == 123
    
    def test_command_with_callback(self):
        """Test command with callback"""
        called = []
        def callback():
            called.append(True)
        
        cmd = Command(CommandType.PLAY, callback=callback)
        assert cmd.callback is not None
        cmd.callback()
        assert called == [True]
    
    def test_command_timestamp(self):
        """Test command timestamp is set automatically"""
        before = time.time()
        cmd = Command(CommandType.PLAY)
        after = time.time()
        
        assert before <= cmd.timestamp <= after
    
    def test_command_repr(self):
        """Test command string representation"""
        cmd1 = Command(CommandType.NEXT)
        assert "next" in repr(cmd1).lower()
        
        cmd2 = Command(CommandType.ADD_ALBUM, data={'album_id': 123})
        assert "add_album" in repr(cmd2).lower()
        assert "data=" in repr(cmd2)


class TestCommandQueue:
    """Test CommandQueue class"""
    
    def test_queue_creation(self):
        """Test queue creation"""
        cq = CommandQueue()
        assert cq.empty()
        assert cq.qsize() == 0
    
    def test_put_and_get(self):
        """Test basic put and get operations"""
        cq = CommandQueue()
        cmd = Command(CommandType.PLAY)
        
        cq.put(cmd)
        assert cq.qsize() == 1
        assert not cq.empty()
        
        retrieved = cq.get(timeout=1)
        assert retrieved.type == CommandType.PLAY
        assert cq.qsize() == 0
        assert cq.empty()
    
    def test_multiple_commands(self):
        """Test multiple commands in queue"""
        cq = CommandQueue()
        
        cq.put(Command(CommandType.PLAY))
        cq.put(Command(CommandType.PAUSE))
        cq.put(Command(CommandType.STOP))
        
        assert cq.qsize() == 3
        
        cmd1 = cq.get()
        assert cmd1.type == CommandType.PLAY
        
        cmd2 = cq.get()
        assert cmd2.type == CommandType.PAUSE
        
        cmd3 = cq.get()
        assert cmd3.type == CommandType.STOP
        
        assert cq.empty()
    
    def test_queue_stats(self):
        """Test queue statistics tracking"""
        cq = CommandQueue()
        
        cq.put(Command(CommandType.PLAY))
        cq.put(Command(CommandType.PAUSE))
        
        stats = cq.get_stats()
        assert stats['total_commands'] == 2
        assert stats['pending'] == 2
        assert stats['processed'] == 0
        
        cq.get()
        stats = cq.get_stats()
        assert stats['pending'] == 1
        
        cq.mark_processed()
        stats = cq.get_stats()
        assert stats['processed'] == 1
    
    def test_mark_error(self):
        """Test error tracking"""
        cq = CommandQueue()
        
        cq.put(Command(CommandType.PLAY))
        cq.get()
        cq.mark_error()
        
        stats = cq.get_stats()
        assert stats['errors'] == 1
    
    def test_reset_stats(self):
        """Test statistics reset"""
        cq = CommandQueue()
        
        cq.put(Command(CommandType.PLAY))
        cq.get()
        cq.mark_processed()
        
        cq.reset_stats()
        stats = cq.get_stats()
        assert stats['total_commands'] == 0
        assert stats['processed'] == 0
    
    def test_thread_safety(self):
        """Test queue is thread-safe"""
        cq = CommandQueue()
        
        def producer():
            for i in range(100):
                cq.put(Command(CommandType.PLAY, data={'index': i}))
        
        def consumer():
            for _ in range(100):
                cq.get(timeout=2)
        
        # Start producers
        producers = [threading.Thread(target=producer) for _ in range(5)]
        for t in producers:
            t.start()
        
        # Wait for all to enqueue
        for t in producers:
            t.join()
        
        # Should have 500 commands (5 threads * 100 each)
        assert cq.qsize() == 500
        
        # Start consumers
        consumers = [threading.Thread(target=consumer) for _ in range(5)]
        for t in consumers:
            t.start()
        
        # Wait for all to consume
        for t in consumers:
            t.join()
        
        # Should be empty
        assert cq.empty()
    
    def test_timeout_on_empty_queue(self):
        """Test get with timeout on empty queue"""
        import queue as queue_module
        
        cq = CommandQueue()
        
        with pytest.raises(queue_module.Empty):
            cq.get(timeout=0.1)
    
    def test_maxsize_limit(self):
        """Test queue size limit"""
        import queue as queue_module
        
        cq = CommandQueue(maxsize=2)
        
        cq.put(Command(CommandType.PLAY))
        cq.put(Command(CommandType.PAUSE))
        
        # Queue is full, should raise Full exception
        with pytest.raises(queue_module.Full):
            cq.put(Command(CommandType.STOP), block=False)


class TestCommandFactory:
    """Test command factory function"""
    
    def test_create_command_without_data(self):
        """Test creating command without data"""
        cmd = create_command(CommandType.PLAY)
        assert cmd.type == CommandType.PLAY
        assert cmd.data is None
    
    def test_create_command_with_data(self):
        """Test creating command with data"""
        cmd = create_command(CommandType.ADD_ALBUM, album_id=123, user='test')
        assert cmd.type == CommandType.ADD_ALBUM
        assert cmd.data['album_id'] == 123
        assert cmd.data['user'] == 'test'
    
    def test_create_command_kwargs(self):
        """Test factory with various kwargs"""
        cmd = create_command(
            CommandType.SET_VOLUME,
            volume=75,
            speaker='Living Room',
            fade=True
        )
        assert cmd.data['volume'] == 75
        assert cmd.data['speaker'] == 'Living Room'
        assert cmd.data['fade'] is True


class TestCommandTypes:
    """Test CommandType enum"""
    
    def test_all_command_types_accessible(self):
        """Test all command types are defined"""
        # Playback
        assert CommandType.PLAY
        assert CommandType.PAUSE
        assert CommandType.STOP
        assert CommandType.NEXT
        assert CommandType.PREV
        
        # Queue
        assert CommandType.ADD_SONG
        assert CommandType.ADD_ALBUM
        assert CommandType.CLEAR_QUEUE
        
        # Settings
        assert CommandType.SET_VOLUME
        assert CommandType.TOGGLE_REPEAT
        assert CommandType.TOGGLE_SHUFFLE
        
        # Internal
        assert CommandType._TRACK_ENDED
        assert CommandType._UPDATE_STATE
    
    def test_command_type_values(self):
        """Test command type string values"""
        assert CommandType.PLAY.value == "play"
        assert CommandType.NEXT.value == "next"
        assert CommandType.ADD_ALBUM.value == "add_album"
        assert CommandType._TRACK_ENDED.value == "_track_ended"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
