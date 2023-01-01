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