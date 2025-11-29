# AI Development Guidelines for TinySonos

This document provides guidelines for AI assistants (Claude, GPT, etc.) contributing to the TinySonos project. It captures the patterns, practices, and architectural decisions that have made this project successful.

---

## Project Philosophy

### Core Principles

1. **Reliability Over Features** - Skip-free playback is non-negotiable
2. **Single Responsibility** - Each component has one clear purpose
3. **Backward Compatibility** - Feature flags enable safe rollback
4. **Observable Behavior** - Extensive logging and statistics
5. **User-Centric Design** - UI responsiveness and feedback matter

### Development Mantras

- "Make it work, make it right, make it fast" - in that order
- "If it's not tested, it's broken"
- "Race conditions are eliminated, not mitigated"
- "Sonos hardware is unreliable, plan accordingly"

---

## Architecture Patterns

### Command-Queue Pattern

**Always use command queues for state-modifying operations.**

```python
# ✅ CORRECT - Serialize through command queue
adapter.enqueue_next()  # Returns immediately
# Command processed async by controller

# ❌ WRONG - Direct manipulation causes races
self.musicqueue.pop()
self.sonos.play_uri(song)
```

**Rationale:** Single-threaded command processing eliminates all race conditions. The queue ensures operations are serialized and predictable.

### State Management

**Controller owns the truth, Sonos is unreliable.**

```python
# ✅ CORRECT - Trust controller state
if self.state == "PLAYING":
    self._handle_next()

# ❌ WRONG - Sonos state can be stale/wrong
sonos_state = self.sonos.get_current_transport_info()
if sonos_state == "PLAYING":  # Unreliable!
```

**Rationale:** Sonos hardware reports inconsistent state. Controller maintains internal state and overrides Sonos when necessary.

### Monitoring Pattern

**Aggressive polling handles Sonos instability.**

```python
# ✅ CORRECT - Poll frequently (0.5s)
while self.running:
    current_state = self.sonos.get_current_transport_info()
    # Detect changes, auto-play, take over
    time.sleep(0.5)

# ❌ WRONG - Rely on events alone
self.sonos.subscribe()  # Events are missed!
```

**Rationale:** Sonos event subscriptions are unreliable. Polling every 0.5s ensures we catch state changes and song endings.

---

## Code Organization

### File Structure

```
TinySonos/
├── server.py           # HTTP server, API gateway
├── src/
│   ├── controller.py   # Playback controller (single thread)
│   ├── adapter.py      # Backward compatibility bridge
│   └── commands.py     # Command system
├── web/
│   ├── index.html      # Main UI
│   └── style.css       # Styling
├── tools/              # Utility scripts
├── tests/              # Test suite
└── media/              # Music library
```

### Module Responsibilities

**server.py:**
- HTTP request handling
- SSE event broadcasting
- Static file serving
- Feature flag management
- **NEVER** direct Sonos manipulation (use adapter)

**controller.py:**
- Command processing
- Queue management
- Sonos control
- State tracking
- Monitoring thread
- **NEVER** HTTP logic (callbacks only)

**adapter.py:**
- API translation
- Command queueing
- State queries
- **NEVER** modify controller internals directly

**commands.py:**
- Command definitions
- Queue implementation
- **NEVER** business logic

---

## Coding Standards

### Logging

**Use appropriate log levels:**

```python
# Debug - verbose operational details
log.debug("Processing command: NEXT")

# Info - significant events
log.info("Queue was empty, auto-starting playback")

# Warning - recoverable issues
log.warning("Sonos state check failed, retrying")

# Error - serious problems
log.error(f"Failed to play song: {e}")
```

**Include context in logs:**

```python
# ✅ GOOD - Helpful context
log.info(f"Added {len(songs)} songs from album {album_id}")

# ❌ BAD - No context
log.info("Added songs")
```

### Error Handling

**Handle Sonos instability gracefully:**

```python
# ✅ CORRECT - Expect failures
try:
    self.sonos.play_uri(song['path'])
except Exception as e:
    log.error(f"Playback failed: {e}")
    # Retry logic or fail gracefully

# ❌ WRONG - Assume success
self.sonos.play_uri(song['path'])  # Can fail!
```

**Return meaningful errors to clients:**

```python
# ✅ GOOD - Actionable error
return json.dumps({
    "error": "Album not found in database",
    "album_id": album_id
})

# ❌ BAD - Cryptic
return json.dumps({"error": "Error"})
```

### Threading

**Minimize thread creation:**

```python
# ✅ GOOD - Single monitoring thread
self.monitor_thread = threading.Thread(
    target=self._monitor_playback,
    daemon=True
)

# ❌ BAD - Thread per operation
for song in queue:
    threading.Thread(target=self.play, args=(song,)).start()
```

**Use thread-safe primitives:**

```python
# ✅ GOOD - queue.Queue is thread-safe
from queue import Queue
self.command_queue = Queue()

# ❌ BAD - Lists aren't thread-safe for concurrent access
self.command_list = []  # Race condition!
```

---

## API Design

### Endpoint Patterns

**Use consistent naming:**

- `/play`, `/pause`, `/stop` - Actions (verbs)
- `/state`, `/queue`, `/playing` - Resources (nouns)
- `/toggle/repeat` - Toggles
- `/album/123`, `/speaker/10.0.1.100` - Resource ID paths

**Return consistent JSON:**

```python
# ✅ GOOD - Consistent structure
{"Response": "OK", "queue_depth": 5}

# ❌ BAD - Inconsistent
"OK"  # Plain string
```

### SSE Events

**Name events by what changed:**

- `track_changed` - New song started
- `playback_state` - State changed
- `queue_changed` - Queue modified
- `volume_changed` - Volume adjusted

**Include complete state in events:**

```python
# ✅ GOOD - Self-contained
sse_broadcast('track_changed', {
    'title': song['title'],
    'artist': song['artist'],
    'album': song['album'],
    'album_art': song.get('album_art', ''),
    'duration': song.get('duration', '0:00:00')
})

# ❌ BAD - Requires additional fetch
sse_broadcast('track_changed', {'song_id': '123'})
```

---

## Frontend Patterns

### SSE + Polling Hybrid

**Use SSE for instant updates, polling for safety:**

```javascript
// ✅ GOOD - Hybrid approach
eventSource.addEventListener('track_changed', updateUI);
setInterval(showprogress, 2000);  // Fallback polling

// ❌ BAD - Polling only (wasteful) or SSE only (fragile)
```

### XML Metadata Fallback

**Parse XML when structured data missing:**

```javascript
// ✅ GOOD - Fallback to XML
let title = data.title;
if (!title && data.metadata) {
    const xml = parser.parseFromString(data.metadata, "text/xml");
    title = xml.getElementsByTagName("dc:title")[0]?.textContent;
}

// ❌ BAD - Assume structured data always present
document.querySelector(".title").innerHTML = data.title;  // Might be empty!
```

### State Indicators

**Distinguish controller state from hardware state:**

```javascript
// ✅ GOOD - Show both states
if (data.sonos_state === 'PLAYING' && data.state === 'STOPPED') {
    showExternalSourceIndicator();
}

// ❌ BAD - Confuse the two
if (data.state === 'PLAYING') {
    // Which state? Controller or Sonos?
}
```

---

## Testing Practices

### Use Mock Objects

**Test without hardware:**

```python
# ✅ GOOD - Mock Sonos
from tests.mock_sonos import MockSonos
controller = PlaybackController(sonos=MockSonos(), ...)

# ❌ BAD - Require real speaker
controller = PlaybackController(sonos=real_sonos, ...)  # Brittle!
```

### Test Critical Paths

**Focus on race-prone operations:**

1. Multiple `/next` calls in sequence
2. Queue operations during playback
3. External source takeover
4. Song ending detection
5. Auto-play triggers

### Integration Tests

**Verify endpoint integration:**

```python
# Test that endpoint routes to adapter correctly
response = requests.get('http://localhost:8000/next')
assert response.json()['Response'] == 'OK'
# Check command was queued
assert controller.command_queue.qsize() > 0
```

---

## Common Pitfalls

### ❌ Race Conditions

```python
# WRONG - Two threads modifying same data
def jukebox_thread():
    song = musicqueue.pop()  # Thread 1
    
def handle_next():
    song = musicqueue.pop()  # Thread 2
    # Both threads might get same song!
```

**Fix:** Use command queue pattern.

### ❌ Trusting Sonos State

```python
# WRONG - Sonos state can be stale
if sonos.get_current_transport_info()['current_transport_state'] == 'PLAYING':
    # Might be wrong!
```

**Fix:** Track state internally in controller.

### ❌ Blocking Operations in Main Thread

```python
# WRONG - Blocks request processing
def do_get(self):
    time.sleep(5)  # Blocks all other requests!
```

**Fix:** Use async commands or background threads.

### ❌ Missing XML Fallback

```python
# WRONG - Assumes title always populated
title = track_info['title']  # Might be empty!
```

**Fix:** Parse from metadata XML when missing.

### ❌ Forgetting Auto-Play Logic

```python
# WRONG - Add to queue but don't start
musicqueue.extend(songs)
# If queue was empty, nothing will play!
```

**Fix:** Check if queue was empty and auto-start.

---

## Feature Flag Pattern

### Adding New Features

**Always add feature flags for major changes:**

```python
# In server.py
USE_NEW_FEATURE = os.getenv('USE_NEW_FEATURE', 'false').lower() == 'true'

# Dual code paths
if USE_NEW_FEATURE:
    new_implementation()
else:
    legacy_implementation()
```

**Benefits:**
- Instant rollback capability
- A/B testing
- Gradual rollout
- Risk mitigation

### Feature Flag Lifecycle

1. **Development:** Default `false`
2. **Testing:** Manually enable with env var
3. **Beta:** Default `true`, but can disable
4. **Stable:** Remove flag, delete legacy code

---

## Documentation Standards

### Code Comments

**Explain WHY, not WHAT:**

```python
# ✅ GOOD - Explains rationale
# Stop current song before playing next to ensure clean transition
# Without this, Sonos sometimes skips or stutters
self.sonos.stop()

# ❌ BAD - States the obvious
# Call stop function
self.sonos.stop()
```

### Docstrings

**Use comprehensive docstrings for public methods:**

```python
def _handle_add_album(self, data: Dict):
    """
    Add entire album to queue.
    
    Args:
        data: Dict containing 'album_id'
        
    Auto-starts playback if queue was empty and controller is in PLAYING state.
    Sends queue_changed SSE event.
    """
```

### README Updates

**Update README when:**
- Adding new features
- Changing configuration
- Adding dependencies
- Modifying architecture

---

## Performance Guidelines

### Acceptable Latencies

- Command queueing: < 5ms
- Command processing: < 50ms
- SSE event delivery: < 100ms
- API response: < 200ms
- State poll: < 10ms

### Optimization Priorities

1. **Correctness** - Never sacrifice reliability for speed
2. **Responsiveness** - Users notice >100ms delays
3. **Resource Usage** - But don't optimize prematurely

### Memory Management

```python
# ✅ GOOD - Limit queue size
MAX_QUEUE_SIZE = 1000
if len(self.musicqueue) >= MAX_QUEUE_SIZE:
    log.warning("Queue at maximum size")
    return

# ❌ BAD - Unbounded growth
self.musicqueue.extend(infinite_songs)  # Memory leak!
```

---

## Debugging Techniques

### Enable Verbose Logging

```python
# Temporarily increase log level
logging.basicConfig(level=logging.DEBUG)
```

### Use /stats Endpoint

```bash
# Check controller health
curl http://localhost:8000/stats
{
    "commands_processed": 150,
    "auto_plays": 45,
    "state": "PLAYING"
}
```

### Monitor SSE Events

```javascript
// Log all SSE events
eventSource.onmessage = (e) => {
    console.log('SSE:', e.type, e.data);
};
```

### Use listen.py Tool

```bash
# Monitor Sonos events directly
python3 tools/listen.py
```

---

## Git Workflow

### Commit Messages

**Use conventional commit format:**

```
feat: Add external source state indicator
fix: Prevent song skipping in /next endpoint
docs: Update API documentation for /location
refactor: Extract command processing to separate module
test: Add tests for queue management
```

### Branch Strategy

- `main` - Stable releases
- `dev` - Integration branch
- `feature/*` - New features
- `fix/*` - Bug fixes

### Before Committing

1. Test with `USE_NEW_CONTROLLER=true`
2. Test with `USE_NEW_CONTROLLER=false`
3. Check for console errors
4. Update relevant documentation
5. Run tests if available

---

## AI-Specific Guidelines

### Understanding Context

**Read these files first when starting:**
1. `API.md` - Full API reference and architecture
2. `RELEASE.md` - Recent changes and history
3. `README.md` - Project overview
4. This file (`CLAUDE.md`) - Development guidelines

### Making Changes

**Before modifying code:**
1. Understand the command-queue pattern
2. Identify which component to change (server/adapter/controller)
3. Consider backward compatibility
4. Plan SSE event updates
5. Think about frontend implications

**When adding features:**
1. Add feature flag if significant
2. Update API.md documentation
3. Update RELEASE.md changelog
4. Add logging at appropriate levels
5. Consider monitoring/stats

**When fixing bugs:**
1. Identify root cause (race condition? state mismatch? Sonos issue?)
2. Fix in appropriate layer (controller for state, adapter for API)
3. Add logging to prevent recurrence
4. Test both feature flag states
5. Document the fix

### Code Review Checklist

Before suggesting code changes, verify:

- [ ] No race conditions introduced
- [ ] Backward compatible (or feature-flagged)
- [ ] Proper error handling
- [ ] Appropriate logging
- [ ] SSE events sent when state changes
- [ ] Frontend updated if needed
- [ ] Documentation updated
- [ ] Consistent with existing patterns

### Communication Style

**Be specific and actionable:**

```
✅ GOOD:
"The issue is in controller.py line 234. The state check happens 
after the Sonos call, but should happen before to respect user 
commands. Move the `if self.state == "PLAYING"` check above 
the `sonos.play_uri()` call."

❌ BAD:
"There's a bug in the controller that needs fixing."
```

**Explain rationale:**

```
✅ GOOD:
"We should poll every 0.5s instead of 1s because Sonos can 
transition between songs in under 1 second, and we need to 
catch those transitions to auto-play the next song."

❌ BAD:
"Change the sleep to 0.5 seconds."
```

### Common Questions to Ask

When analyzing the code:

1. Does this operation modify state? → Use command queue
2. Does this need UI update? → Send SSE event
3. Can Sonos fail here? → Add try/except
4. Is this a critical path? → Add extensive logging
5. Does this change behavior? → Add feature flag
6. Will users notice delay? → Optimize or make async

---

## Project History Context

### Why This Architecture?

**Original Problem:**
- Users reported songs skipping when clicking "next"
- Queue would lose songs randomly
- Playback would stop after one song

**Root Cause:**
- Race condition between jukebox thread and `/next` endpoint
- Both threads popping from same queue simultaneously
- No synchronization mechanism

**Solution Evolution:**
1. Analyzed architecture (identified race condition)
2. Proposed command-queue pattern
3. Implemented controller with single-threaded processing
4. Added monitoring thread for auto-play
5. Integrated with feature flag for safety
6. Enhanced with "supreme master" takeover mode

### Key Decisions

**Single-threaded controller:**
- Eliminates ALL race conditions
- Simplifies state management
- Predictable operation ordering

**0.5 second polling:**
- Matches original jukebox frequency
- Catches song endings reliably
- Overhead is negligible

**Feature flag:**
- Allows instant rollback
- De-risks deployment
- Enables gradual migration

**Internal state tracking:**
- Sonos hardware state is unreliable
- Controller knows the truth
- Override Sonos when necessary

---

## Success Metrics

### What "Good" Looks Like

**Reliability:**
- Zero song skips in normal operation
- Auto-play success rate > 99%
- Controller uptime matches server uptime

**Performance:**
- API response < 200ms
- SSE events delivered < 100ms
- Song transitions < 2 seconds

**User Experience:**
- UI updates within 100ms of state change
- Album art always displays
- Queue display always accurate

**Code Quality:**
- All public methods documented
- Error handling on every Sonos call
- Logging for all state transitions
- Tests for critical paths

---

## Resources

### Key Files
- `API.md` - Complete API reference
- `RELEASE.md` - Version history
- `README.md` - User documentation
- `src/controller.py` - Core playback logic
- `tests/mock_sonos.py` - Testing without hardware

### External Documentation
- [SoCo Library](https://github.com/SoCo/SoCo) - Sonos control
- [Sonos API](https://developer.sonos.com/) - Official docs
- [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) - SSE spec

### Tools
- `tools/listen.py` - Monitor Sonos events
- `tools/check_metadata.py` - Verify audio file metadata
- `tests/test_controller.py` - Controller unit tests

---

## Final Thoughts

### The TinySonos Way

1. **Reliability First** - Skip-free playback is the entire point
2. **Trust Internal State** - Sonos hardware lies, believe the controller
3. **Serialize Operations** - Command queue eliminates races
4. **Monitor Aggressively** - Poll frequently, catch everything
5. **Fail Gracefully** - Sonos will fail, handle it elegantly
6. **Stay Observable** - Log everything, expose stats
7. **Keep It Simple** - Complexity is the enemy of reliability

### When In Doubt

- Add more logging
- Check the command queue
- Trust the controller state
- Test with feature flag both ways
- Read the Sonos docs again (they're often wrong)
- Remember: it's probably a race condition

---

**Welcome to TinySonos development! May your playlists never skip. 🎵**
