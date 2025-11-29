# Tools

## PlexExportM3U - Export Plex Playlist to M3U Format

This tool connects to your Plex server and exports all of the
audio playlists to m3u8 files. 

### Usage

```bash
# Install plexapi library
pip3 install plexapi

# Run export tool
python3 PlexExportM3U.py <Plex_Host> <Plex_Token> <Dest_Dir>
```

* Plex_Host - Base URL for Plex Server (e.g. http://10.1.1.10:32400)
* Plex_Token - see https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/
* Dest_Dir - Location to store m3u8 files (default: `./`)

## PlexExportSongs - Export Plex Database and Album Art

This tool connects to your Plex server and exports all of the
metadata for the audio library, including the album art. 

### Usage

```bash
# Run export tool
python3 PlexExportSongs.py <Plex_Host> <Plex_Token> <Dest_Dir>
```

* Plex_Host - Base URL for Plex Server (e.g. http://10.1.1.10:32400)
* Plex_Token - see https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/
* Dest_Dir - Location to store metabase files and album-art (default: `./`)

### Database

The export tool will create several files in the Dest_Dir location:

* Album Art - A directory will be created, `album-art/` that will contain `{X}.png` files where {X} is the Plex key ID for album.  This same key ID is exported with the PlexExportM3U.py tool for reference and easy display of album art.
* db.json - This contains a list of all the albums in the library along with all the tracks, artist name, media file path, etc.
* db.*.json - These are index files providing fast reference, specifically:
    * db.albums.json - List of album title to album key (1:n)
    * db.added.json - List of timestamps to albums showing when albums were added to library (e.g. most recently added) (n:n)
    * db.artist.json - List of artist name to album keys (1:n)
    * db.songs.json - List of song names to album keys (1:n)
    * db.songkey.json - List of song key to album key (1:1)

### Credits
* This is based on the great work by evolve700 at https://github.com/evolve700/PlexPlaylistExport
* plexapi Project - https://github.com/pkkid/python-plexapi 


## check_metadata - Audio Metadata and Album Art Checker

This tool checks audio files for embedded metadata including album art.
It's useful for verifying that your music files have proper tags and artwork
that will be displayed by Sonos players and the TinySonos UI.

### Supported Formats
- MP3 (ID3 tags)
- M4A/MP4 (iTunes/Apple tags)
- FLAC
- And other formats supported by mutagen

### What it checks
- Title, Artist, Album, Date, Genre metadata
- Embedded album artwork (presence, format, size)
- File format detection

### Usage

```bash
# Install required library
pip3 install mutagen

# Check a single file
python3 check_metadata.py /path/to/song.mp3

# Check multiple files
python3 check_metadata.py /path/to/album/*.mp3

# Check all files in a directory (recursive)
python3 check_metadata.py /path/to/music/**/*.m4a
```

### Example Output

```
============================================================
Checking: /media/Music/Artist/Album/song.m4a
============================================================

File Type: MP4

Metadata Tags:
------------------------------------------------------------
  Title       : Song Title
  Artist      : Artist Name
  Album       : Album Name
  Date        : 2023
  Genre       : Pop

============================================================
Album Art Check:
============================================================
✅ Album art FOUND! (1 image(s))

  Image 1:
    Type: Cover
    MIME: image/jpeg
    Size: 71,115 bytes (69.4 KB)
```

## listen - Sonos Event Monitor

This tool subscribes to Sonos events and displays real-time updates from the speaker.
It's useful for debugging and understanding how Sonos reports state changes.

### What it monitors
- **renderingControl** events (volume changes, mute state, etc.)
- **avTransport** events (playback state: PLAYING, PAUSED_PLAYBACK, TRANSITIONING, STOPPED)

### Usage

```bash
# Run the event listener
python3 listen.py
```

The script will:
1. Auto-discover a Sonos speaker on your network
2. Subscribe to renderingControl and avTransport events
3. Display events in real-time as they occur
4. Press Ctrl+C to stop

### Example Output

```
Living Room
** renderingControl **
{'volume': {'LF': '100', 'Master': '15', 'RF': '100'}}

** avTransport **
{'transport_state': 'PLAYING'}

** avTransport **
{'transport_state': 'PAUSED_PLAYBACK'}
```

This is helpful for:
- Understanding Sonos state transitions
- Debugging controller behavior
- Monitoring external control (Alexa, Apple Music, etc.)
