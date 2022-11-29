# TinySonos
Simple web service to control [Sonos](https://www.sonos.com/) speakers and play files from your local computer.

## Setup

Edit these two variables in `server.py` or set in environment before running service:
* MEDIAPATH - Root folder for all Media files
* DROPPREFIX - Drop this URL prefix from any playlist or file selected. 

Playlists are defined using the `m3u` / `m3u8` format (file extension). This format is used by Plex, iTunes, VLC Media Player, Windows Media Player, and many others. For TinySonos to find these,  playlist files (*.m3u or *.m3u8) need to be in the MEDIAPATH root.

## Run

```python
# Run Server
python3 server.py
```

The services will auto-discover your Sonos system and will attach to the first zone it finds.

TinySonos Control Panel: http://localhost:8001/

## Docker Run [Optional]

Run the Server as a Docker Container listening on port 8001 and 54000. Make sure you update the media path, MEDIAPATH and DROPPREFIX below to match your setup.

```bash
docker run \
-d \
-p 8001:8001 \
-p 54000:54000 \
-e MEDIAPATH='/media' \
-e DROPPREFIX='/media' \
-v /Volumes/Plex:/media:ro \
--name tinysonos \
--user ${UID} \
--restart unless-stopped \
jasonacox/tinysonos
```

## Credits

* This project uses the python library `soco` to access the Sonos APIs. See this project at: https://github.com/SoCo/SoCo
* This project was inspired by the `soco-cli` project that expaned on `soco` to demonstarte how using a simple HTTP server could provide local file access to Sonos.  See the project at: https://github.com/avantrec/soco-cli