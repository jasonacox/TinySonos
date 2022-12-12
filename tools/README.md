# Tools

## PlexExportM3U - Export Plex Playlist to M3U Format

This tool connects to your Plex server and exports all of the
audio playlists to m3u8 files. 

### Usage

```bash
python3 PlexExportM3U.py <Plex_Host> <Plex_Token> <Dest_Dir>
```

* Plex_Host - Base URL for Plex Server (e.g. http://10.1.1.10:32400)
* Plex_Token - see https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/
* Dest_Dir - Location to store m3u8 files (default: `./`)

### Requirements

* Python Library plexapi (pip install plexapi)
* Plex Token (X-Plex-Token) = see (Plex Help to get Token)[https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/]

### Credits
* This is based on the great work by evolve700 at https://github.com/evolve700/PlexPlaylistExport
* plexapi Project - https://github.com/pkkid/python-plexapi 