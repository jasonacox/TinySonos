# TinySonos Architecture Analysis & Proposal

## Current Architecture Issues

### 1. **Race Conditions & Concurrency Problems**

#### Problem: Multiple Code Paths Modifying Shared State
- **`/next` endpoint** directly pops from `musicqueue` and calls `sonos.play_uri()`
- **`jukebox()` thread** also pops from `musicqueue` when state != "PLAYING"
- **No locking mechanism** protects the shared `musicqueue`, `playing`, `stop` globals
- **Result**: Double-skipping songs because both paths can pop simultaneously

```python
# CURRENT UNSAFE PATTERN:
# /next endpoint (API thread)
playing = musicqueue.pop(0)  # Thread 1
sonos.play_uri(playing['path'])

# jukebox thread (separate thread)
if state != "PLAYING":
    playing = musicqueue.pop(0)  # Thread 2 - RACE!
```

#### Problem: Global Variables Without Thread Safety
```python
# These are accessed by multiple threads without locks:
musicqueue = []     # Modified by: API handlers, jukebox thread
playing = {}        # Modified by: /next, /prev, jukebox thread
stop = False        # Modified by: /play, /pause, /stop, /next
state = None        # Modified by: jukebox thread
```

### 2. **Unclear Separation of Responsibilities**

#### Who Controls Playback?
- **API handlers** directly call `sonos.play_uri()`, `sonos.stop()`, etc.
- **jukebox thread** also calls `sonos.play_uri()`
- **No single source of truth** for playback control
- **Result**: Commands conflict, state becomes inconsistent

#### Who Manages the Queue?
- Queue modified in multiple places without coordination
- No atomic operations for queue management
- SSE broadcasts happen inconsistently (sometimes yes, sometimes no)

### 3. **Polling-Based State Detection**

```python
# jukebox thread polls every 0.5s
while running:
    if len(musicqueue) > 0 and not stop:
        state = sonos.get_current_transport_info()['current_transport_state']
        if state != "PLAYING":
            # Play next song
    time.sleep(0.5)  # Wasteful polling
```

**Problems**:
- Wastes CPU checking state 2x per second even when idle
- 500ms latency to detect song endings
- Doesn't scale with multiple clients
- Misses rapid state changes

### 4. **SSE Monitor Also Polls**

```python
# sse_monitor() polls every 0.2s
while running:
    track_info = current_sonos.get_current_track_info()
    # Compare with cached state
    time.sleep(0.2)  # More wasteful polling
```

**Problems**:
- Duplicate work (both jukebox and SSE monitor check Sonos state)
- SSE checks every 200ms, jukebox every 500ms
- No event-driven architecture
- Two threads doing similar work inefficiently

### 5. **Fragile `stop` Flag Logic**

```python
# /play endpoint
stop = False
sonos.play()

# /pause endpoint  
stop = True
sonos.pause()

# jukebox thread
if len(musicqueue) > 0 and not stop:  # Relies on flag
```

**Problems**:
- `stop` flag easily gets out of sync with actual Sonos state
- No recovery if flag is wrong
- Manual play/pause confuses jukebox thread
- Flag doesn't survive crashes/restarts

### 6. **Missing Multi-Client Coordination**

**Current assumption**: Single user controlling the system
**Reality**: Multiple browser tabs, mobile devices, API clients

**Problems**:
- No request queuing or serialization
- No optimistic locking
- No conflict resolution
- Commands from different clients can interleave unpredictably

---

## Proposed Robust Architecture

### **Core Principle: Single-Threaded Command Queue with Event-Driven State**

```
┌─────────────────────────────────────────────────────┐
│              HTTP API Handlers                      │
│  (Multiple threads, but don't modify state)         │
└──────────────┬──────────────────────────────────────┘
               │ Commands via Queue
               ▼
┌─────────────────────────────────────────────────────┐
│         Playback Controller (Single Thread)         │
│  - Processes commands from queue                    │
│  - Manages musicqueue (exclusive owner)             │
│  - Calls Sonos API (single point of control)        │
│  - Broadcasts SSE events                            │
│  - Event-driven (not polling)                       │
└──────────────┬──────────────────────────────────────┘
               │ Events
               ▼
┌─────────────────────────────────────────────────────┐
│              Sonos Event Listener                   │
│  - Subscribe to track_changed, playback_state       │
│  - Push events to controller                        │
└─────────────────────────────────────────────────────┘
```

### **1. Command Queue Pattern**

Replace direct Sonos API calls with command queue:

```python
import queue
import threading
from dataclasses import dataclass
from enum import Enum

class CommandType(Enum):
    PLAY = "play"
    PAUSE = "pause"
    STOP = "stop"
    NEXT = "next"
    PREV = "prev"
    ADD_SONG = "add_song"
    ADD_ALBUM = "add_album"
    SET_VOLUME = "set_volume"
    CLEAR_QUEUE = "clear_queue"

@dataclass
class Command:
    type: CommandType
    data: dict = None
    callback: callable = None  # For getting results back

# Global command queue (thread-safe)
command_queue = queue.Queue()

# API handlers just enqueue commands
def handle_next():
    command_queue.put(Command(CommandType.NEXT))
    return {"status": "ok"}

def handle_add_album(album_id):
    command_queue.put(Command(CommandType.ADD_ALBUM, {"album_id": album_id}))
    return {"status": "ok"}
```

### **2. Playback Controller (Single Thread)**

One thread processes all commands and manages all state:

```python
class PlaybackController:
    def __init__(self, sonos):
        self.sonos = sonos
        self.musicqueue = []
        self.playing = {}
        self.state = "STOPPED"
        self.repeat = False
        self.shuffle = False
        self.running = True
        self.lock = threading.Lock()  # For read-only access from other threads
        
    def run(self):
        """Main controller loop - processes commands and events"""
        while self.running:
            try:
                # Process commands with timeout (non-blocking)
                try:
                    cmd = command_queue.get(timeout=0.1)
                    self._process_command(cmd)
                except queue.Empty:
                    pass
                    
            except Exception as e:
                log.error(f"Controller error: {e}")
    
    def _process_command(self, cmd: Command):
        """Process a single command (runs in controller thread only)"""
        if cmd.type == CommandType.NEXT:
            self._play_next()
        elif cmd.type == CommandType.ADD_ALBUM:
            self._add_album(cmd.data['album_id'])
        elif cmd.type == CommandType.PAUSE:
            self._pause()
        # ... etc
        
    def _play_next(self):
        """Play next song from queue"""
        if not self.musicqueue:
            log.info("Queue empty, nothing to play")
            return
            
        # Pop next song
        self.playing = self.musicqueue.pop(0)
        if self.repeat:
            self.musicqueue.append(self.playing)
        
        # Play it
        self.sonos.play_uri(self.playing['path'])
        self.state = "PLAYING"
        
        # Broadcast to all clients
        self._broadcast_track_changed()
        self._broadcast_queue_changed()
        
        log.info(f"Now playing: {self.playing.get('title', 'Unknown')}")
    
    def _add_album(self, album_id):
        """Add album to queue"""
        # Load from db
        songs = self._load_album_songs(album_id)
        self.musicqueue.extend(songs)
        self._broadcast_queue_changed()
        log.info(f"Added {len(songs)} songs to queue")
    
    def _broadcast_track_changed(self):
        """Send SSE event to all clients"""
        sse_broadcast('track_changed', {
            'title': self.playing.get('title', ''),
            'artist': self.playing.get('artist', ''),
            'album': self.playing.get('album', ''),
            'album_art': self.playing.get('album_art', '')
        })
    
    def _broadcast_queue_changed(self):
        sse_broadcast('queue_changed', {'queuedepth': len(self.musicqueue)})
    
    def get_state(self):
        """Thread-safe state access for API handlers"""
        with self.lock:
            return {
                'playing': self.playing.copy(),
                'queue_depth': len(self.musicqueue),
                'state': self.state,
                'repeat': self.repeat,
                'shuffle': self.shuffle
            }
```

### **3. Event-Driven State Updates**

Replace polling with Sonos event subscriptions:

```python
from soco.events import event_listener

class SonosEventHandler:
    def __init__(self, controller, sonos):
        self.controller = controller
        self.sonos = sonos
        self.subscription = None
        
    def start(self):
        """Subscribe to Sonos events"""
        # Subscribe to transport events (play/pause/stop/track changes)
        self.subscription = self.sonos.avTransport.subscribe(
            auto_renew=True,
            event_queue=None  # Use callback instead
        )
        self.subscription.callback = self._on_event
        
    def _on_event(self, event):
        """Handle Sonos events"""
        # Parse event
        state = event.variables.get('transport_state')
        track = event.variables.get('current_track_meta_data')
        
        # Send command to controller based on event
        if state == "STOPPED" and self.controller.musicqueue:
            # Song ended, queue next one
            command_queue.put(Command(CommandType.NEXT))
        elif state == "PAUSED":
            # Update state
            command_queue.put(Command(CommandType._UPDATE_STATE, {"state": "PAUSED"}))
        
        log.debug(f"Sonos event: {state}")
```

**Benefits**:
- No polling overhead
- Instant response to Sonos state changes
- Works even if user controls Sonos directly (via app/voice)
- Automatically detects song endings

### **4. Thread-Safe Read Access**

API handlers need to read state without blocking:

```python
# In API handler
def handle_get_state():
    """API endpoint to get current state"""
    # Controller provides thread-safe snapshot
    state = controller.get_state()
    return json.dumps(state)

def handle_get_queue():
    """API endpoint to get queue"""
    with controller.lock:
        # Quick read with lock
        queue_copy = controller.musicqueue.copy()
    return json.dumps(queue_copy)
```

### **5. Unified SSE Broadcasting**

All SSE broadcasts happen from controller only:

```python
class PlaybackController:
    # ...
    
    def _notify_clients(self, event_type, data):
        """Single point for all client notifications"""
        sse_broadcast(event_type, data)
        log.debug(f"SSE: {event_type} -> {len(sse_clients)} clients")
```

**Benefits**:
- Consistent event ordering
- No duplicate or conflicting events
- Easy to debug (single notification point)

### **6. Atomic Operations**

Use context managers for complex operations:

```python
class PlaybackController:
    def _shuffle_queue(self):
        """Atomically shuffle the queue"""
        import random
        # Everything happens in controller thread, naturally atomic
        random.shuffle(self.musicqueue)
        self._broadcast_queue_changed()
    
    def _clear_and_add_album(self, album_id):
        """Atomically replace queue with album"""
        self.musicqueue.clear()
        songs = self._load_album_songs(album_id)
        self.musicqueue.extend(songs)
        self._broadcast_queue_changed()
        # No race condition possible!
```

---

## Migration Strategy

### **Phase 1: Add Command Queue (Non-Breaking)**

1. Create `Command` class and `command_queue`
2. Create `PlaybackController` class
3. Keep existing code working
4. Gradually route commands through queue
5. Test each endpoint migration

### **Phase 2: Consolidate State Management**

1. Move `musicqueue`, `playing`, etc. into `PlaybackController`
2. Remove global variables
3. Add thread-safe getters
4. Update API handlers to use getters

### **Phase 3: Event-Driven Updates**

1. Add Sonos event subscription
2. Remove jukebox polling thread
3. Remove SSE monitor polling
4. All updates driven by events

### **Phase 4: Cleanup**

1. Remove `stop` flag (use actual state)
2. Remove duplicate SSE broadcast calls
3. Simplify API handlers (just enqueue commands)
4. Add comprehensive logging

---

## Benefits of Proposed Architecture

### **Correctness**
✅ No race conditions (single thread modifies state)
✅ No double-skipping (commands serialized)
✅ Consistent state across clients
✅ Atomic operations

### **Performance**
✅ No wasteful polling (event-driven)
✅ Faster response (events vs 200-500ms polls)
✅ Lower CPU usage (idle when inactive)
✅ Scales to more clients

### **Maintainability**
✅ Clear separation of concerns
✅ Single source of truth for playback
✅ Easy to add new commands
✅ Easy to debug (command log)

### **Reliability**
✅ Commands survive transient Sonos errors
✅ Can add retry logic easily
✅ State recovery on restart
✅ Works with external Sonos control

---

## Code Size Comparison

**Current**: ~1100 lines with race conditions
**Proposed**: ~800 lines, cleaner separation, safer

---

## Implementation Checklist

- [ ] Create `Command` and `CommandType` classes
- [ ] Create `PlaybackController` class
- [ ] Route `/next` through command queue
- [ ] Route `/play`, `/pause`, `/stop` through queue
- [ ] Route queue management (`/albumadd`, etc.) through queue
- [ ] Subscribe to Sonos events
- [ ] Remove jukebox polling thread
- [ ] Remove SSE monitor polling
- [ ] Add thread-safe state getters
- [ ] Move globals into controller
- [ ] Add logging for all commands
- [ ] Add error recovery
- [ ] Test with multiple concurrent clients
- [ ] Performance testing

---

## Immediate Quick Fix (Without Full Refactor)

If you want a quick fix NOW without the full refactor:

```python
# Add a lock at the top
import threading
playback_lock = threading.Lock()

# Modify /next endpoint:
elif self.path == '/next':
    with playback_lock:  # Prevent concurrent access
        if len(musicqueue) > 0:
            playing = musicqueue.pop(0)
            if repeat:
                musicqueue.append(playing)
            sonos.play_uri(playing['path'])
            sse_broadcast('track_changed', {...})
            sse_broadcast('queue_changed', {...})

# Modify jukebox thread:
def jukebox():
    while running:
        with playback_lock:  # Prevent concurrent access
            if len(musicqueue) > 0 and not stop:
                state = sonos.get_current_transport_info()['current_transport_state']
                if state != "PLAYING":
                    playing = musicqueue.pop(0)
                    # ... rest of code
        time.sleep(0.5)
```

This adds basic locking but doesn't solve the architectural issues.

---

## Recommendation

**Implement the full Command Queue architecture** for long-term robustness. The code will be:
- Cleaner
- Safer  
- Faster
- Easier to maintain
- Ready for multiple clients

The refactor is ~1-2 days of work but will eliminate classes of bugs permanently.
