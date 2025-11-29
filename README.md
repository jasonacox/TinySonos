# TinySonos
Simple web service to control [Sonos](https://www.sonos.com/) speakers and play files from your local computer.

**NEW in v0.1.0:** Hyper-aggressive playback controller that eliminates song skipping and ensures continuous music playback!

<img width="800" alt="image" src="https://user-images.githubusercontent.com/836718/209888864-29897828-789f-477b-a1f8-77ecbf8552ad.png">

## Features

* **🎵 Hyper-Aggressive Playback** - Revolutionary command-queue architecture ensures seamless, continuous playback without skipping
* **🎯 Supreme Master Mode** - Automatically takes control from external sources (Alexa, Apple Music) when you have songs queued
* **Web-Based Control Panel** - Intuitive interface for controlling Sonos speakers with real-time updates
* **Local Media Playback** - Stream audio files from your computer to Sonos
* **Playlist Support** - Load and play M3U/M3U8 playlists
* **Multi-Room Audio** - Join/unjoin speakers to create groups
* **Volume Control** - Individual speaker and group volume management
* **Album Browser** - Browse your music library by albums, artists, and recently added
* **Plex Integration** - Export Plex playlists and metadata (see `tools/` directory)
* **RESTful API** - Full API access for automation and integration
* **Real-Time Updates** - Server-Sent Events (SSE) for instant UI updates

## What's New in v0.1.0

### Playback Engine
TinySonos now features a completely rewritten playback controller that:
- **Eliminates Race Conditions**: Single-threaded command-queue ensures reliable operation
- **Aggressive Auto-Play**: Monitors every 0.5 seconds to instantly queue the next song
- **Takes Control**: Automatically stops external sources (Alexa, Apple Music) when you have songs queued
- **Respects Your Commands**: Honors explicit stop/pause from UI while aggressively managing the queue
- **Never Skips**: Robust architecture prevents the song skipping issues that plague native Sonos

### Enhanced UI/UX
- Queue display shows currently playing track with ▶ icon
- "Up Next" section clearly shows queued songs
- Control panel buttons highlight current state
- Playlist names display without .m3u8 extension
- Album art updates more reliably
- Speaker table auto-sizes to content

### Developer Tools
- New `tools/check_metadata.py` - Verify audio file metadata and embedded album art
- Enhanced logging and statistics tracking
- Feature flag system for safe rollback (`USE_NEW_CONTROLLER`)

See [RELEASE.md](RELEASE.md) for complete changelog.

## Requirements

* Python 3.7+
* Sonos speakers on the same local network
* Audio files accessible on your computer

## Setup

Edit these variables in `server.py` or set in environment before running service:
* `MEDIAPATH` - Root folder for all media files
* `M3UPATH` - Location of M3U playlist files (defaults to MEDIAPATH)
* `DROPPREFIX` - Comma-separated list of URL prefixes to remove from playlist paths (e.g., "/media,/mnt,/Volumes")
* `USE_NEW_CONTROLLER` - Enable new playback controller (default: "true", set to "false" for legacy mode)

Playlists are defined using the `m3u` / `m3u8` format (file extension). This format is used by Plex, iTunes, VLC Media Player, Windows Media Player, and many others. For TinySonos to find these, playlist files (*.m3u or *.m3u8) need to be in the MEDIAPATH root.

## Local Development Setup

```bash
# Set paths (optional - edit defaults in server.py instead)
export MEDIAPATH="/path/to/your/media"
export M3UPATH="/path/to/your/playlists"

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run server
python3 server.py
```

**TinySonos Control Panel:** http://localhost:8001/

**Ports:**
* `8001` - API and web interface
* `54000` - Media file server (used by Sonos to stream audio)

## Plex Integration

TinySonos includes tools to export Plex playlists and metadata. See the [`tools/`](tools/) directory for:

* **check_metadata.py** - Verify audio file metadata and embedded album art (MP3, M4A, FLAC)
* **PlexExportM3U.py** - Export Plex playlists to M3U format
* **PlexExportSongs.py** - Export Plex metadata and album art for enhanced browsing

These tools are optional but enhance the TinySonos experience with album art and rich metadata.

## API Endpoints

TinySonos provides a RESTful API for automation and integration:

**Playback Control:**
* `/play`, `/pause`, `/stop` - Transport controls
* `/next`, `/prev` - Track navigation
* `/toggle/shuffle`, `/toggle/repeat` - Playback modes

**Speaker Management:**
* `/speakers` - List all speakers with status
* `/setzone/{ip}` - Set coordinator zone
* `/speaker_join/{ip}` - Join speaker to group
* `/speaker_unjoin/{ip}` - Remove speaker from group
* `/volume/{level}` - Set group volume (or `/volume/up`, `/volume/down`, `/volume/mute`)
* `/speaker_vol/{ip}/{level}` - Set individual speaker volume

**Library & Queue:**
* `/listm3u` - List available playlists
* `/playlist/{name}` - Load playlist into queue
* `/albums/all`, `/albums/recent` - Browse albums
* `/album/{id}` - Get album details
* `/albumadd/{id}` - Add album to queue
* `/addsong/{key}` - Add single song to queue
* `/queue` - View current queue
* `/queue/clear` - Clear queue

**Status:**
* `/current` - Currently playing track info
* `/state` - Player state (playing/paused/stopped)
* `/stats` - Server statistics

## Docker Run [Optional]

Run the Server as a Docker Container.  The container runs in host network mode so it can hear UDP multicast broadcast from Sonos devices. Make sure you update the media path, MEDIAPATH, M3UPATH and DROPPREFIX below to match your setup.

```bash
docker run \
-d \
--network host \
-e MEDIAPATH='/media' \
-e M3UPATH='/media' \
-e DROPPREFIX='/media' \
-e USE_NEW_CONTROLLER='true' \
-v /media:/media:ro \
--name tinysonos \
--user ${UID} \
--restart unless-stopped \
jasonacox/tinysonos
```

## Architecture

TinySonos v0.1.0 features a robust command-queue architecture:

- **PlaybackController** - Single-threaded controller that manages all playback state and operations
- **Command Queue** - Serializes all operations to eliminate race conditions
- **Monitoring Thread** - Polls Sonos state every 0.5 seconds to detect song endings and auto-play next track
- **Feature Flag** - `USE_NEW_CONTROLLER` environment variable enables instant rollback to legacy mode if needed

The new architecture ensures reliable, continuous playback while respecting user commands (stop/pause) and aggressively taking control from external sources when you have songs queued.

## Credits

* This project uses the python library `soco` to access the Sonos APIs. See this project at: https://github.com/SoCo/SoCo
* This project was inspired by the `soco-cli` project that expanded on `soco` to demonstrated how using a simple HTTP server could provide local file access to Sonos.  See the project at: https://github.com/avantrec/soco-cli
* Player UI code based on the great work by Annie Wu, https://github.com/anniedotexe/music-player with custom SVG Paths created at https://yqnn.github.io/svg-path-editor/ 
