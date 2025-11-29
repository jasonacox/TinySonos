# Release Notes

## 📋 Future Development (TODO)

### High Priority
- [ ] **FastAPI Migration**
  - Migrate from http.server to FastAPI + Uvicorn
  - Async/await support for better concurrency
  - Automatic OpenAPI/Swagger documentation
  - Pydantic models for request/response validation
  - WebSocket support (can replace/complement SSE)
  - Type hints and better IDE support
  - Backward compatible endpoints during migration

- [ ] **Enhanced Queue Management**
  - Reorder songs in queue (drag-and-drop)
  - Remove individual songs by index
  - Save/load queue as playlist
  - Queue history and restoration

- [ ] **Event-Driven Architecture Completion**
  - Reduce polling frequency by improving SSE reliability
  - Add WebSocket support for bidirectional communication
  - Implement heartbeat mechanism for connection monitoring

- [ ] **Comprehensive Testing**
  - Automated integration tests for all endpoints
  - End-to-end SSE event stream tests
  - External source takeover scenario tests
  - Edge case coverage (empty queue, network errors, etc.)

### Medium Priority
- [ ] **Search & Browse Enhancements**
  - Artist browsing with album listings
  - Advanced search with filters (year, genre, etc.)
  - Search history and favorites
  - "Now Playing" artist/album quick navigation

- [ ] **Playlist Management**
  - Create/edit/delete playlists via UI
  - Smart playlists with auto-update rules
  - Playlist import/export (M3U, Spotify, etc.)
  - Collaborative playlists

- [ ] **Authentication & Security**
  - Multi-user support with authentication
  - Role-based access control
  - API rate limiting
  - Secure token-based API access

### Low Priority
- [ ] **Advanced Features**
  - Crossfade between tracks
  - Equalizer controls
  - Sleep timer
  - Alarm/wake-up scheduling
  - Podcast support

- [ ] **API Improvements**
  - REST API versioning (v2)
  - GraphQL API option
  - Swagger/OpenAPI documentation
  - API client libraries (Python, JavaScript)

- [ ] **Performance Optimization**
  - Database indexing improvements
  - Album art caching strategy
  - Progressive loading for large libraries
  - CDN support for media files

### Infrastructure
- [ ] **Production Deployment**
  - Docker Compose with monitoring
  - Kubernetes deployment templates
  - Health check endpoints
  - Metrics and observability (Prometheus/Grafana)

- [ ] **Documentation**
  - Video tutorials
  - Troubleshooting guide expansion
  - Architecture decision records (ADRs)
  - Contributing guidelines

---

## v0.1.0 - Hyper-Aggressive Playback Controller (Current)

This is a **major release** that introduces a revolutionary hyper-aggressive playback controller. The new architecture eliminates race conditions and ensures seamless, continuous music playback without the skipping issues that plague native Sonos.

### 🎯 Core Architecture Changes
- **New Playback Controller**: Single-threaded command-queue architecture eliminates race conditions
- **Hyper-Aggressive Playback**: 0.5-second monitoring ensures seamless song transitions
- **State Management**: Controller tracks internal state, overriding unreliable Sonos hardware state
- **Supreme Master Mode**: TinySonos takes control from external sources (Alexa, Apple Music) when queue has songs
- **User Command Respect**: Explicitly honors stop/pause commands from UI while aggressively auto-playing queue

### ✨ New Features
- **Feature Flag System**: `USE_NEW_CONTROLLER` environment variable (default: "true") enables instant rollback
- **Dual Code Paths**: Legacy and new controller paths for safe migration
- **Monitoring Thread**: Detects song endings and auto-plays next track with 0.5s polling
- **External Source Takeover**: Automatically stops external players when TinySonos has queued songs
- **Smart Album Art**: Uses controller's album art for managed content, Sonos art for external sources
- **Enhanced Queue Display**: Shows currently playing track with ▶ icon, "Up Next" section for queued songs
- **Playlist Name Cleanup**: Removes .m3u8 extension from playlist display
- **Multiple Path Prefix Support**: DROPPREFIX environment variable now accepts comma-separated list
- **Auto-Start Playback**: Automatically starts playing when adding songs/playlists to empty queue

### 🎨 UI/UX Improvements
- **Control Panel State Display**: Shows current playback state (playing/paused/stopped) with button highlighting
- **Bottom Controls Action Display**: Shows next available action (play when stopped, pause when playing)
- **Speaker Table Auto-Width**: Table only expands to fit content, left-justified in container
- **Album Art Reliability**: Polling updates ensure album art displays even when SSE events are missed
- **State Initialization**: Page load now fetches initial state to set correct button highlights

### 🛠️ Developer Tools
- **Metadata Checker**: New `tools/check_metadata.py` script to verify audio file metadata and album art
  - Supports MP3, M4A/MP4, FLAC formats
  - Shows embedded album artwork presence, format, and size
  - Displays title, artist, album, genre metadata

### 🐛 Bug Fixes
- Fixed song skipping issues when clicking next button
- Fixed album art flipping to placeholder during long song playback
- Fixed control panel buttons not highlighting correctly on page load
- Fixed /setzone endpoint to return proper JSON response
- Fixed auto-play not working when loading playlist into empty queue
- Fixed time counter running when playback stopped
- Fixed playlist not continuing after first song (added monitoring thread)

### 📝 Code Quality
- New modular architecture: `src/controller.py`, `src/commands.py`, `src/adapter.py`
- Comprehensive logging for debugging and monitoring
- Thread-safe state access with read/write locks
- Statistics tracking (songs played, auto-plays, commands processed)
- Clean separation of concerns (command queue, controller, adapter)

### ⚙️ Configuration
- `USE_NEW_CONTROLLER`: Enable/disable new controller (default: "true")
- `DROPPREFIX`: Comma-separated list of path prefixes to remove from file paths

### 🔄 Migration Notes
- Existing installations automatically use new controller
- Set `USE_NEW_CONTROLLER=false` to revert to legacy behavior if needed
- All endpoints maintain backward compatibility

## v0.0.27
- **UI/UX Enhancements**:
  - Redesigned disconnect button with eject icon (⏏) replacing "do not enter" emoji
  - Integrated Main Volume control into speaker table for consistent layout
  - Added styled speaker panel with surface background, rounded corners, and shadow
  - Aligned player and speaker panels with consistent top spacing
  - Alphabetically sorted speaker names in speaker list
  - Improved dark mode theme with better contrast and readability
  - Added top border to "Songs in Queue" heading for visual separation
  - Enhanced CSS with theme-aware variables for colors, surfaces, and shadows
  - Improved null-safety in DOM updates to prevent JavaScript errors
- **Code Quality**:
  - Refactored speaker table rendering for better maintainability
  - Added safety checks for DOM element updates to prevent null reference errors
  - Improved CSS organization and consistency

## v0.0.26
- Added Server-Sent Events (SSE) for real-time updates without polling
  - Real-time track changes, playback state, volume, and speaker updates
  - Automatic reconnection with exponential backoff
  - Graceful fallback to polling when SSE disconnected
- Improved play/pause button UX to show next action instead of current state
- Added "Disconnect" control to clear external music sources (Apple Music, Spotify, etc.)
- Enhanced browser refresh handling with clean SSE reconnection
- Added speaker join/unjoin functionality via web interface
- Clickable speaker status indicators to activate/deactivate speakers in group
- Enhanced speaker table display with Up/Down volume buttons
- Added `requirements.txt` for Python dependencies
- Improved documentation with local development setup instructions
- Suppressed connection reset error stack traces for cleaner logs

## v0.0.25
- Enhanced speaker volume control with individual sliders
- Improved multi-speaker management interface
- Added mute functionality for individual speakers
- Refined speaker table layout

## v0.0.24
- Bug fixes and stability improvements
- Code cleanup and optimization

## Earlier Versions (v0.0.1 - v0.0.23)

### Core Features
- **Web-Based Control Panel** - Interactive Sonos controller with modern UI
- **Media Server** - HTTP server on port 54000 for streaming local files to Sonos
- **API Server** - RESTful API on port 8001 for control and automation
- **Playlist Support** - M3U/M3U8 playlist loading and playback
- **Album Browser** - Browse music by albums, artists, recently added
- **Queue Management** - Manage playback queue with shuffle/repeat modes
- **Volume Control** - Group and individual speaker volume management
- **Plex Integration Tools**:
  - PlexExportM3U.py - Export Plex playlists to M3U format
  - PlexExportSongs.py - Export Plex metadata and album art
- **Docker Support** - Containerized deployment option
- **Auto-Discovery** - Automatic Sonos system detection

### Technical Details
- Built with Python 3
- Uses SoCo library for Sonos API integration
- Range HTTP server for media streaming
- Threading for concurrent API and media serving
- JSON-based metadata database support

## Initial Release (November 2022)
First public release of TinySonos - A simple web service to control Sonos speakers and play files from your local computer.
