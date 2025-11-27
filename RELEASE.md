# Release Notes

## v0.0.26 (Current)
- Added speaker join/unjoin functionality via web interface
- Clickable speaker status indicators to activate/deactivate speakers in group
- Enhanced speaker table display with Up/Down volume buttons
- Added `requirements.txt` for Python dependencies
- Improved documentation with local development setup instructions

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
