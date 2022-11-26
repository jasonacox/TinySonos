# TinySonos
Simple web service to control Sonos speakers and play files from your local host.


## Setup

Edit these two variables in `server.py` or set in envrionment before running service:
* MEDIAPATH - Root folder for all Media files
* DROPPREFIX - Drop this URL prefix from any playlist or file selected. 

Your playlists (m3u or m3u8 files) need to be in the MEDIAPATH root.

## Use

```python
# Run Server
python3 server.py
```

The services will auto-discover your Sonos system and will attatch to the first zone it finds.

Control: http://localhost:8001/


