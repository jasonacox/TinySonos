# TinySonos
Simple web service to control [Sonos](https://www.sonos.com/) speakers and play files from your local computer.

<img width="800" alt="image" src="https://user-images.githubusercontent.com/836718/209888864-29897828-789f-477b-a1f8-77ecbf8552ad.png">

## Features

* **Web-Based Control Panel** - Intuitive interface for controlling Sonos speakers
* **Local Media Playback** - Stream audio files from your computer to Sonos
* **Playlist Support** - Load and play M3U/M3U8 playlists
* **Multi-Room Audio** - Join/unjoin speakers to create groups
* **Volume Control** - Individual speaker and group volume management
* **Album Browser** - Browse your music library by albums, artists, and recently added
* **Plex Integration** - Export Plex playlists and metadata (see `tools/` directory)
* **RESTful API** - Full API access for automation and integration

## Requirements

* Python 3.7+
* Sonos speakers on the same local network
* Audio files accessible on your computer

## Setup

Edit these two variables in `server.py` or set in environment before running service:
* MEDIAPATH - Root folder for all Media files
* M3UPATH - Location of M3U playlist files (defaults to MEDIAPATH)
* DROPPREFIX - Drop this URL prefix from any playlist or file selected

Playlists are defined using the `m3u` / `m3u8` format (file extension). This format is used by Plex, iTunes, VLC Media Player, Windows Media Player, and many others. For TinySonos to find these,  playlist files (*.m3u or *.m3u8) need to be in the MEDIAPATH root.

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
-v /media:/media:ro \
--name tinysonos \
--user ${UID} \
--restart unless-stopped \
jasonacox/tinysonos
```

## Credits

* This project uses the python library `soco` to access the Sonos APIs. See this project at: https://github.com/SoCo/SoCo
* This project was inspired by the `soco-cli` project that expanded on `soco` to demonstrated how using a simple HTTP server could provide local file access to Sonos.  See the project at: https://github.com/avantrec/soco-cli
* Player UI code based on the great work by Annie Wu, https://github.com/anniedotexe/music-player with custom SVG Paths created at https://yqnn.github.io/svg-path-editor/ 
