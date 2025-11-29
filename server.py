# TinySonos - Web Based Sonos Controller
# -*- coding: utf-8 -*-
"""
Web Based Control Panel and Jukebox for Sonos WiFi Speaker System. This provides
ability to control and play audio files from a localhost/server on a Sonos system,
including multiple audio file formats and m3u playlist.

Author: Jason A. Cox
Date: November 23, 2022
For more information see https://github.com/jasonacox/tinysonos

Description
    Server provides web based control panel on local TCP 8001 and a Sonos
    compatible media file server on TCP 54000.  

    Setup - edit defaults below or send as environmental variables
    Install - pip3 install requests soco rangehttpserver
    Run - python3 server.py
    Test - http://localhost:8001

Credits:
    * https://github.com/SoCo/SoCo
    * https://github.com/avantrec/soco-cli

"""

# Modules
import threading
import time
import logging
import json
import requests
import resource
import sys
import socket
import os
import random
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from socketserver import ThreadingMixIn 
from RangeHTTPServer import RangeRequestHandler  # type: ignore
from queue import Empty
from soco.events import event_listener
import soco # type: ignore

BUILD = "0.1.0"  # Major release: Command-queue architecture with hyper-aggressive playback controller

# Defaults
APIPORT = 8001
MEDIAPORT = 54000
DEBUGMODE = False
MEDIAPATH = "/Volumes/Plex"  # Location of media files
MAXPAYLOAD = 4000            # Reject payload if above this size
DROPPREFIX = ["/media"]      # Optional - Omit media filename prefix(es)

# Environment config
M3UPATH = os.getenv("M3UPATH", MEDIAPATH) 
MEDIAPATH = os.getenv("MEDIAPATH", MEDIAPATH)
MEDIAHOST = os.getenv("MEDIAHOST", None)
# Parse DROPPREFIX as comma-separated list
dropprefix_env = os.getenv("DROPPREFIX", ",".join(DROPPREFIX))
DROPPREFIX = [prefix.strip() for prefix in dropprefix_env.split(",") if prefix.strip()]
DEBUGMODE = os.getenv("DEBUGMODE", str(DEBUGMODE)).lower() in ("true", "1", "yes")

# Static Assets
web_root = os.path.join(os.path.dirname(__file__), "web")

# ContentType Map - File ext to filetype
CTMAP = {
            '': 'application/octet-stream',
            '.manifest': 'text/cache-manifest',
            '.html': 'text/html',
            '.png': 'image/png',
            '.jpg': 'image/jpg',
            '.svg':	'image/svg+xml',
            '.css':	'text/css',
            '.js':'application/x-javascript',
            '.wasm': 'application/wasm',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.mp3': 'audio/mpeg', 
            '.m4a': 'audio/mp4', 
            '.mp4': 'audio/mp4',
            '.ogg': 'audio/ogg',
            '.oga': 'audio/ogg',
            '.gz': 'application/gzip', 
            '.Z': 'application/octet-stream', 
            '.bz2': 'application/x-bzip2', 
            '.xz': 'application/x-xz',
        }

# Logging
log = logging.getLogger(__name__)
logging.basicConfig(format='%(levelname)s:%(message)s',level=logging.INFO)
log.setLevel(logging.INFO)

# Global Stats
serverstats = {}
serverstats['tinysonos'] = BUILD
serverstats['soco'] = soco.__version__
serverstats['gets'] = 0
serverstats['posts'] = 0
serverstats['errors'] = 0
serverstats['timeout'] = 0
serverstats['api'] = {}
serverstats['ts'] = int(time.time())         # Timestamp for Now
serverstats['start'] = int(time.time())      # Timestamp for Start 
playlists = {}
musicqueue = []     # Jukebox queue of music files
zone = None         # Zone to use
state = None
repeat = False
shuffle = True
stop = False
playing = {}        # Current song

# Global Song Metabase
db = {}
db_added = {}
db_albums = {}
db_artists = {}
db_songs = {}
db_songkey = {}
db_filetime = 0

# Global Variables
running = True

# SSE (Server-Sent Events) Support
import queue
sse_clients = []  # List of SSE client queues
sse_state = {
    'last_track': None,
    'last_state': None,
    'last_volume': None,
    'last_speakers': None,
    'last_queue_depth': 0
}

# Set up Sonos
sonos = list(soco.discover())[0]
sonos = sonos.group.coordinator
zone = sonos.ip_address

# Initialize controller architecture
from src.controller import PlaybackController
from src.adapter import ControllerAdapter

log.info("=" * 60)
log.info("CONTROLLER ARCHITECTURE")
log.info("=" * 60)

# Create controller
controller = PlaybackController(
    sonos=sonos,
    db=db,
    db_songkey=db_songkey,
    mediahost=MEDIAHOST if MEDIAHOST else socket.gethostbyname(socket.gethostname()),
    mediaport=MEDIAPORT,
    mediapath=MEDIAPATH
)

# Create adapter for backward compatibility
adapter = ControllerAdapter(controller)

# Start controller thread
controller.start()

# Connect SSE callbacks for real-time client updates
controller.on_track_changed = lambda data: sse_broadcast('track_changed', data)
controller.on_queue_changed = lambda data: sse_broadcast('queue_changed', data)
controller.on_state_changed = lambda data: sse_broadcast('playback_state', data)
controller.on_volume_changed = lambda data: sse_broadcast('volume_changed', data)

log.info("PlaybackController: Started successfully")
log.info("Adapter: Created")
log.info("SSE Callbacks: Connected to controller")
log.info("=" * 60)

# Helpful Functions

def formatreturn(value):
    if value is None:
        result = {"status": "OK"}
    elif type(value) is dict:
        result = value
    else:
        result = {"status": value}
    return(json.dumps(result))


def get_static(web_root, fpath):
    """Return static file with content type"""
    if fpath.split('?')[0] == "/":
        fpath = "index.html"
    if fpath.startswith("/"):
        fpath = fpath[1:]
    fpath = fpath.split("?")[0]
    freq = os.path.join(web_root, fpath)
    if os.path.exists(freq):
        ext = os.path.splitext(fpath)[1]
        if ext in CTMAP:
            ftype = CTMAP[ext]
        else:
            ftype = 'text/plain'
        log.debug("MEDIA: url = {} contenttype = {}".format(fpath,ftype))
        with open(freq, 'rb') as f:
            return f.read(), ftype
    return None, None

def detect_ip_address():
    """Return the local ip-address"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    s.close()
    return ip_address

def load_db():
    """ Load database and index """
    global db, db_added, db_albums, db_artists, db_songs, db_songkey, db_filetime
    try:
        filetime = os.path.getmtime("%s/db.json" % MEDIAPATH)
        if filetime > db_filetime:
            log.info("Loading song metabase")
            db_filetime = filetime
            f = open("%s/db.json" % MEDIAPATH)
            db = json.load(f)
            f = open("%s/db.added.json" % MEDIAPATH)
            db_added = json.load(f)
            f = open("%s/db.albums.json" % MEDIAPATH)
            db_albums = json.load(f)
            f = open("%s/db.artists.json" % MEDIAPATH)
            db_artists = json.load(f)
            f = open("%s/db.songs.json" % MEDIAPATH)
            db_songs = json.load(f)
            f = open("%s/db.songkey.json" % MEDIAPATH)
            db_songkey = json.load(f)
            log.info("DB Loaded: %d albums, %d songs, %d artists" % (len(db_albums), len(db_songs), len(db_artists)))
    except:
        log.info("Error loading song metabase data.")

# Determine my Hostname
if MEDIAHOST is None:
    MEDIAHOST = detect_ip_address()

# Parse file contents of file with m3u or m3u8 extension
#  Return array of dict {'length': None, 'title': None, 'path': None}
def parse_m3u(m3u_file):
    with open(m3u_file, "r") as infile:
        if m3u_file.lower().endswith(".m3u") or m3u_file.lower().endswith(".m3u8"):
            line = infile.readline()
            if not line.startswith("#EXTM3U"):
                log.debug("File '{}' lacks '#EXTM3U' as first line".format(m3u_file))
                return []
        playlist = []
        id = 0
        song = {'id': id, 'length': None, 'title': None, 'path': None, 'album': None, 'artist': None, 'albumartist': None, 'skey': None, 'akey': None}
        for line in infile:
            line = line.strip()
            if line.startswith("#EXTINF:"):  # song artist - title
                length, title = line.split("#EXTINF:")[1].split(",", 1)
                song['length'] = length
                artist = None
                if " - " in title:
                    pak = title.split(" - ")
                    artist=pak[0]
                    title=pak[1]
                song['title'] = title
                song['artist'] = artist
            elif line.startswith("#PLEX"): # Plex index keys
                #PLEX ALBUM=33,SONG=38
                vals = line.split(",")
                song['akey'] = int(vals[0].split("=")[1])
                song['skey'] = int(vals[1].split("=")[1])
            elif line.startswith("#EXTALB:"): # album
                album = line.split("#EXTALB:")[1]
                song['album'] = album
            elif line.startswith("#EXTART:"): # album artist
                albumartist = line.split("#EXTART:")[1]
                song['albumartist'] = albumartist
            elif line.startswith("#"):
                # Ignore comment lines
                pass
            elif len(line) != 0:
                id = id + 1
                song['path'] = line
                # TODO: Restrict to only MEDIAPATH
                playlist.append(song)
                song = {'id': id, 'length': None, 'title': None, 'path': None, 'album': None, 'artist': None, 'albumartist': None, 'skey': None, 'akey': None}
        return playlist

# Scan path for m3u and m3u8 files
#  Return array of playlist m3u files 
def list_m3u(path):
    m3u = []
    ext = (".m3u",".m3u8")
    if path.endswith("/"):
        path = path[:-1]
    for file in os.listdir(path):
        if file.lower().endswith(tuple(ext)):
            m3u.append(file)
    return m3u


# Handlers

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    pass

## MEDIA Server Handler

class mediahandler(RangeRequestHandler):
    def __init__(self, *args, **kwargs):
        self.extensions_map = CTMAP
        super().__init__(*args, directory=MEDIAPATH, **kwargs)

    def log_message(self, format, *args):
        if DEBUGMODE:
            sys.stderr.write("%s - - [%s] %s\n" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format%args))
        else:
            pass

    def address_string(self):
        # replace function to avoid lookup delays
        host, hostport = self.client_address[:2]
        return host

    def do_GET(self):
        log.debug("GET - Path = {}".format(self.path))
        # Remove any matching prefix from DROPPREFIX array
        original_path = self.path
        for prefix in DROPPREFIX:
            if self.path.startswith(prefix):
                self.path = self.path[len(prefix):]
                break
        if original_path != self.path:
            log.debug("    - converted Path = {}".format(self.path))
        try:
            super().do_GET()
        except Exception as e:
            # It's normal to hit some exceptions with Sonos
            log.debug("Exception ignored: {}".format(e))

## API Server Handler

class apihandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        if DEBUGMODE:
            sys.stderr.write("%s - - [%s] %s\n" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format%args))
        else:
            pass

    def address_string(self):
        # replace function to avoid lookup delays
        host, hostport = self.client_address[:2]
        return host
    
    def handle(self):
        """Handle multiple requests if necessary, suppressing connection reset errors."""
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError) as e:
            # Normal during browser refresh - log at debug level only
            log.debug(f"Connection closed by client: {e}")
        except Exception as e:
            # Log other exceptions normally
            log.error(f"Error handling request: {e}")

    def do_GET(self):
        global musicqueue, zone, sonos, shuffle, repeat, state, stop, playing
        global db, db_added, db_albums, db_artists, db_songs, db_songkey, db_filetime
        global controller, adapter, serverstats
        self.send_response(200)
        message = json.dumps({"Response": "OK"})
        contenttype = 'application/json'
        
        # SSE Endpoint - Server-Sent Events for real-time updates
        if self.path == '/events':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Create a queue for this client
            client_queue = queue.Queue()
            sse_clients.append(client_queue)
            log.info(f"SSE: New client connected, total clients: {len(sse_clients)}")
            
            try:
                # Send initial connection event
                self.wfile.write(b'event: connected\n')
                self.wfile.write(b'data: {"status": "connected"}\n\n')
                self.wfile.flush()
                
                # Stream events to this client
                while running:
                    try:
                        # Wait for events with timeout to allow checking running flag
                        event = client_queue.get(timeout=1.0)
                        self.wfile.write(f'event: {event["type"]}\n'.encode('utf-8'))
                        self.wfile.write(f'data: {json.dumps(event["data"])}\n\n'.encode('utf-8'))
                        self.wfile.flush()
                    except queue.Empty:
                        # Send keepalive comment every second
                        self.wfile.write(b': keepalive\n\n')
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        log.info("SSE: Client disconnected")
                        break
            except Exception as e:
                log.warning(f"SSE: Connection error: {e}")
            finally:
                # Remove client queue when connection closes
                if client_queue in sse_clients:
                    sse_clients.remove(client_queue)
                log.info(f"SSE: Client removed, remaining clients: {len(sse_clients)}")
            return
            
        if self.path== '/current':
            # What is currently playing
            try:
                sonos = soco.SoCo(zone).group.coordinator
                c = sonos.get_current_track_info().copy()
                state = sonos.get_current_transport_info()['current_transport_state']
                c['state'] = state
                if 'album_art' in playing:
                    c['album_art2'] = playing['album_art']
                message = json.dumps(c)
            except Exception as e:
                logging.warning(f"Timeout getting current track info: {e}")
                message = json.dumps({"title": "", "artist": "", "album": "", "position": "0:00:00", "duration": "0:00:00", "state": "STOPPED"})
        elif self.path == '/location':
            # Give location in song
            c = sonos.get_current_track_info()
            
            # Get actual Sonos hardware state
            sonos_transport_state = sonos.get_current_transport_info()['current_transport_state']
            c['sonos_state'] = sonos_transport_state
            
            # Override state and album_art with controller data
            full_state = adapter.get_full_state()
            c['state'] = full_state['state']
            # Use controller's album_art if we're managing playback
            # Otherwise keep Sonos's album_art (for external sources like Alexa, Apple Music)
            if full_state['playing'] and 'album_art' in full_state['playing']:
                c['album_art'] = full_state['playing']['album_art']
            
            message = json.dumps(c)
        elif self.path == '/queuedepth':
            # Give queue depth
            message = json.dumps({"queuedepth": len(adapter.get_queue_copy())})
        elif self.path== '/state':
            # Get state from controller
            full_state = adapter.get_full_state()
            s = {
                'state': full_state['state'],
                'zone': zone,
                'repeat': full_state['repeat'],
                'shuffle': full_state['shuffle'],
                'volume': sonos.group.volume
            }
            message = json.dumps(s)
        elif self.path == '/speakers':
            # List of Sonos Speakers
            log.debug("speakers: Getting speaker list")
            if zone is None:
                log.warning("speakers: Zone is None, discovering speakers")
                sonos = list(soco.discover())[0]
                sonos = sonos.group.coordinator
                zone = sonos.ip_address
                log.info(f"speakers: Set zone to {zone}")
            
            speakers = {}
            discovered = list(soco.discover())
            log.debug(f"speakers: Found {len(discovered)} speakers")
            current_zone = soco.SoCo(zone)
            log.debug(f"speakers: Current zone coordinator: {current_zone.group.coordinator.player_name} at {current_zone.group.coordinator.ip_address}")
            
            for z in discovered:
                log.debug(f"speakers: Processing speaker {z.player_name} at {z.ip_address}")
                speakers[z.player_name] = {}
                speakers[z.player_name]["ip"] = z.ip_address
                speakers[z.player_name]["coordinator"] = soco.SoCo(z.ip_address).group.coordinator == soco.SoCo(z.ip_address)
                # Check if this speaker is a member of the current zone's group
                member = soco.SoCo(z.ip_address) in current_zone.group.members
                speakers[z.player_name]["state"] = member
                speakers[z.player_name]["volume"] = z.volume
                log.debug(f"speakers: {z.player_name} - coordinator: {speakers[z.player_name]['coordinator']}, in_group: {member}, volume: {z.volume}")
            
            message = json.dumps(speakers)
            log.debug(f"speakers: Returning {len(speakers)} speakers")
        elif self.path.startswith('/speaker_join/'):
            # Join a speaker to the coordinator's group
            ip = self.path.split('/speaker_join/')[1]
            log.info(f"speaker_join: Attempting to join speaker at {ip}")
            try:
                # Get the current coordinator
                current_zone = soco.SoCo(zone)
                log.info(f"speaker_join: Current zone: {zone}, Coordinator: {current_zone.group.coordinator.ip_address}")
                coordinator = current_zone.group.coordinator
                log.info(f"speaker_join: Coordinator player: {coordinator.player_name} at {coordinator.ip_address}")
                
                # Get the speaker to join
                speaker = soco.SoCo(ip)
                log.info(f"speaker_join: Target speaker: {speaker.player_name} at {ip}")
                log.info(f"speaker_join: Target speaker current group: {speaker.group.coordinator.player_name}")
                
                # Join the coordinator's group
                speaker.join(coordinator)
                log.info(f"speaker_join: Successfully joined {speaker.player_name} to {coordinator.player_name}'s group")
                message = json.dumps({"Response": f"Speaker {speaker.player_name} joined group"})
            except Exception as e:
                log.error(f"speaker_join: Error joining speaker at {ip}: {str(e)}")
                log.error(f"speaker_join: Exception type: {type(e).__name__}")
                import traceback
                log.error(f"speaker_join: Traceback: {traceback.format_exc()}")
                message = json.dumps({"Response": f"Error: {str(e)}"})
        elif self.path.startswith('/speaker_unjoin/'):
            # Remove a speaker from the group
            ip = self.path.split('/speaker_unjoin/')[1]
            log.info(f"speaker_unjoin: Attempting to remove speaker at {ip} from group")
            try:
                speaker = soco.SoCo(ip)
                log.info(f"speaker_unjoin: Speaker: {speaker.player_name} at {ip}")
                log.info(f"speaker_unjoin: Current group coordinator: {speaker.group.coordinator.player_name}")
                speaker.unjoin()
                log.info(f"speaker_unjoin: Successfully removed {speaker.player_name} from group")
                message = json.dumps({"Response": f"Speaker {speaker.player_name} left group"})
            except Exception as e:
                log.error(f"speaker_unjoin: Error removing speaker at {ip}: {str(e)}")
                log.error(f"speaker_unjoin: Exception type: {type(e).__name__}")
                import traceback
                log.error(f"speaker_unjoin: Traceback: {traceback.format_exc()}")
                message = json.dumps({"Response": f"Error: {str(e)}"})
        elif self.path.startswith('/speaker_vol/'):
            # Set volume for a specific group
            ip, updown = self.path.split('/speaker_vol/')[1].split('/')
            if updown == "up":
                vol = soco.SoCo(ip).volume + 1
            elif updown == "down":
                vol = soco.SoCo(ip).volume - 1
            elif updown == "mute":
                vol = 0
            elif updown.isdigit():
                vol = int(updown)
            else:
                vol = soco.SoCo(ip).volume
            #soco.SoCo(ip).ramp_to_volume(int(vol))
            soco.SoCo(ip).volume = int(vol)
            message = json.dumps({"Response": "OK"})
        elif self.path.startswith('/volume/'):
            # Set volume - route through controller for proper queuing and SSE notification
            updown = self.path.split('/volume/')[1].split('/')[0]
            if updown == "up":
                adapter.enqueue_volume_up()
            elif updown == "down":
                adapter.enqueue_volume_down()
            elif updown == "mute":
                adapter.enqueue_set_volume(0)
            elif updown.isdigit():
                adapter.enqueue_set_volume(int(updown))
            message = json.dumps({"Response": "OK"})
        elif self.path.startswith('/setzone/'):
            zone = self.path.split('/setzone/')[1]
            try:
                # Switch controller to the specified coordinator
                adapter.enqueue_switch_zone(zone)
                # Also update global sonos reference for speaker list queries
                sonos = soco.SoCo(zone).group.coordinator
                log.info(f"Switched coordinator to {zone} ({sonos.player_name})")
                message = json.dumps({"Response": "OK", "coordinator": zone, "name": sonos.player_name})
            except Exception as e:
                log.error(f"Failed to switch to zone {zone}: {e}")
                message = json.dumps({"Error": str(e)})
        elif self.path == '/stats':
            # Give Internal Stats
            serverstats['ts'] = int(time.time())
            serverstats['mem'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            serverstats['controller'] = controller.get_stats()
            
            message = json.dumps(serverstats)
        elif self.path == '/queue':
            # Return current queue
            message = json.dumps(adapter.get_queue_copy())
        elif self.path == '/queue/clear':
            # Clear current queue
            adapter.enqueue_clear_queue()
        elif self.path== '/play':
            adapter.enqueue_play()
        elif self.path== '/pause':
            adapter.enqueue_pause()
        elif self.path== '/stop':
            adapter.enqueue_stop()
        elif self.path== '/disconnect':
            # Disconnect from external music sources by stopping and clearing queue
            try:
                sonos.stop()
                sonos.clear_queue()
            except Exception as e:
                log.debug(f"Disconnect: {e}")
        elif self.path== '/volumeup':
            adapter.enqueue_volume_up()
        elif self.path== '/volumedown':
            adapter.enqueue_volume_down()
        elif self.path== '/next':
            adapter.enqueue_next()
        elif self.path== '/prev':
            adapter.enqueue_prev()
        elif self.path=='/toggle/repeat':
            adapter.enqueue_toggle_repeat()
        elif self.path=='/toggle/shuffle':
            adapter.enqueue_toggle_shuffle()
        elif self.path== '/rescan':
            # rescan/rediscover sonos system zones
            sonos = list(soco.discover())[0]
            sonos = sonos.group.coordinator
            zone = sonos.ip_address
        elif self.path== '/sonos':
            s = {}
            s['household_id'] = sonos.household_id
            s['uid'] = sonos.uid
            message = json.dumps(s)
        elif self.path=='/playing':
            message = json.dumps(adapter.get_playing_copy())
        elif self.path == '/listm3u' or self.path == '/playlists':
            # List all m3u files in M3UPATH
            message = json.dumps(list_m3u(M3UPATH))
        elif self.path.startswith('/showplaylist/'):
            # Return full playlist payload - file specified in URI
            playlistfile = self.path.split('/showplaylist/')[1]
            playlistfile = requests.utils.unquote(playlistfile)
            playlist = parse_m3u("{}/{}".format(M3UPATH,playlistfile))
            message = json.dumps(playlist)
        elif self.path.startswith('/playlist/'):
            # Load playlist into queue - file in URI
            # TODO: Add title and other details
            playlistfile = self.path.split('/playlist/')[1]
            playlistfile = requests.utils.unquote(playlistfile)
            playlist = parse_m3u("{}/{}".format(M3UPATH,playlistfile))
            songs = []
            for item in playlist:
                songs.append(item)
            
            # Controller handles shuffle internally based on current setting
            should_shuffle = adapter.shuffle
            if should_shuffle:
                random.shuffle(songs)
            
            # Build song list for controller
            formatted_songs = []
            for item in songs:
                song = {}
                song['id'] = item['id']
                song['title'] = item['title']
                song['artist'] = item['artist']
                song['length'] = item['length']
                song['album'] = item['album']
                song['albumartist'] = item['albumartist']
                song['path'] = "http://%s:%d%s" % (MEDIAHOST,
                    MEDIAPORT, requests.utils.quote(item['path']))
                album_art = None
                if item['akey'] and os.path.isfile("%s/album-art/%s.png" % (MEDIAPATH, item['akey'])):
                    album_art = "http://%s:%d/album-art/%s.png" % (MEDIAHOST,
                        MEDIAPORT, item['akey'])
                song['album_art'] = album_art
                song['akey'] = item['akey']
                song['skey'] = item['skey']
                formatted_songs.append(song)
            
            adapter.enqueue_add_songs(formatted_songs)
            message = json.dumps({"Response": "Added {} Songs".format(len(formatted_songs))})
        elif self.path.startswith('/addsong/'):
            # Load single song into queue - key in URI
            key = self.path.split('/addsong/')[1]
            albumtracks = db[str(db_songkey[key][0])]['tracks']
            for track in albumtracks:
                if albumtracks[track]['key'] == key:
                    item = albumtracks[track]
                    break
            log.debug(item)
            song = {}
            song['id'] = item['key']
            song['title'] = item['song']
            song['artist'] = item['artist']
            song['length'] = item['length']
            song['album'] = db[str(db_songkey[key][0])]['title']
            song['path'] = "http://%s:%d/%s" % (MEDIAHOST, 
                MEDIAPORT, requests.utils.quote(item['path'][0]))
            album_art = None
            song['akey'] = db_songkey[key][0]
            song['skey'] = key
            if song['akey'] and os.path.isfile("%s/album-art/%s.png" % (MEDIAPATH, song['akey'])):
                album_art = "http://%s:%d/album-art/%s.png" % (MEDIAHOST,
                    MEDIAPORT, song['akey'])
            song['album_art'] = album_art
            
            adapter.enqueue_add_songs([song])
            
            message = json.dumps({"Response": "Added 1 Song"})
        elif self.path.startswith('/playfile/'):
            # Load single song into queue - file in URI
            # TODO: Add other details
            playfile = self.path.split('/playfile/')[1]
            song = {}
            #fn = requests.utils.unquote(self.path.split('/play_file/')[1])
            log.debug("Add PlayFile: {}".format(playfile))
            song['path'] = "http://%s:%d/%s" % (MEDIAHOST, MEDIAPORT, playfile)
            
            adapter.enqueue_add_songs([song])
            
            message = json.dumps({"Response": "Added 1 Song"})
        # TODO
        # elif self.path == '/select/albums':
        elif self.path.startswith("/albumlist/"):
            album_sel = self.path.split('/albumlist/')[1]
            albums = []
            for item in db_albums:
                if album_sel != '' and (item[:len(album_sel)].lower() != album_sel.lower()):
                    continue
                for key in db_albums[item]:
                    a = dict()
                    a["key"] = key
                    a["title"] = db[str(key)]["title"]
                    a["thumbfile"] = db[str(key)]["thumbfile"]
                    a["artist"] = db[str(key)]["artist"]
                    a["added"] = db[str(key)]["added"]
                    a["tracks"] = len(db[str(key)]["tracks"])
                    albums.append(a)
            message = json.dumps(albums)
        elif self.path.startswith("/album/"):
            album_id = self.path.split('/album/')[1]
            if album_id.isdigit() and str(album_id) in db:
                message = json.dumps(db[str(album_id)])
            else:
                message = json.dumps(None)
        elif self.path == '/albums/recent':
            # show last 50 recently added albums
            albums = []
            count = 0
            for a in db_added:
                count += 1
                if count > 50:
                    break
                album_id = db_added[a]
                album = db[str(album_id)]
                album["key"] = album_id
                album["songs"] = len(album["tracks"])
                albums.append(album)
            message = json.dumps(albums)
        elif self.path == '/albums/all':
            # show all albums
            albums = []
            count = 0
            for a in db_albums:
                for album_id in db_albums[a]:
                    album = db[str(album_id)]
                    album["key"] = album_id
                    album["songs"] = len(album["tracks"])
                    albums.append(album)
            message = json.dumps(albums)
        elif self.path.startswith("/albumadd/"):
            album_id = self.path.split('/albumadd/')[1]
            if album_id.isdigit() and str(album_id) in db:
                # Enqueue album via controller
                adapter.enqueue_add_album(album_id)
                # Get count from db for response
                count = len(db[str(album_id)]["tracks"])
                message = json.dumps({"Response": "Added %d Songs" % count})
            else:
                message = json.dumps(None)   
        elif self.path == "/db":
            message = json.dumps(db)  
        elif self.path == "/loaddb":
            db_filetime = 0
            load_db()
            message = json.dumps({"Response": "DB Loaded: %d albums, %d songs, %d artists" % (len(db_albums), len(db_songs), len(db_artists))})
        else:
            # First check to see of song metabase has changed and load
            load_db()
            # Serve static assets from web root first, if found.
            fcontent, ftype = get_static(web_root, self.path)
            if fcontent:
                self.send_header('Content-type','{}'.format(ftype))
                self.send_header('Content-Length', str(len(fcontent)))
                self.end_headers()
                self.wfile.write(fcontent)
                return
            else:
                message = "404 Error"
                log.debug("404 Error: ",self.path)

        # Counts 
        if "Error" in message:
            serverstats['errors'] = serverstats['errors'] + 1
        serverstats['gets'] = serverstats['gets'] + 1
        """
        # Count all API calls
        if self.path in serverstats['api']:
            serverstats['api'][self.path] += 1
        else:
            serverstats['api'][self.path] = 1
        """
        # Send headers and payload
        self.send_header('Content-type',contenttype)
        self.send_header('Content-Length', str(len(message)))
        self.end_headers()
        try:
            # try to send payload
            self.wfile.write(bytes(message, "utf8"))
        except Exception as e:
            # if it fails, log error and continue
            log.debug("Error sending payload: {}".format(e))
            pass
        
# Threads

# Threads

def sse_broadcast(event_type, data):
    """Send event to all connected SSE clients"""
    if not sse_clients:
        return
    
    event = {
        'type': event_type,
        'data': data
    }
    
    # Send to all clients
    for client_queue in sse_clients:
        try:
            client_queue.put_nowait(event)
        except queue.Full:
            log.warning("SSE: Client queue full, skipping event")

def api(port):
    """
    API Server - Thread to listen for commands on port 
    """
    global running
    log.info("Started API server thread on %d", port)

    with ThreadingHTTPServer(('', port), apihandler) as server:
        try:
            # server.serve_forever()
            while running:
                server.handle_request()
        except:
            log.debug('CANCEL')
    log.info('api Exit')

def media(port):
    """
    Media Server - Thread to listening for requests 
    """
    global running
    log.info("Started Media server thread on %d", port)

    with ThreadingHTTPServer(('', port), mediahandler) as server:
        try:
            # server.serve_forever()
            while running:
                server.handle_request()
        except:
            log.debug('CANCEL')
    log.info('media Exit')

# MAIN Thread
if __name__ == "__main__":
    # creating thread
    apiServer = threading.Thread(target=api, args=(APIPORT,))
    mediaServer = threading.Thread(target=media, args=(MEDIAPORT,))
    
    log.info("Controller Mode: Jukebox handled by PlaybackController")
    
    log.info(
        "TinySonos [v%s - SoCo %s] - Web Based Sonos Controller and Jukebox"
        % (BUILD, soco.__version__)
    )

    # try to load metabase
    load_db()

    # start threads
    apiServer.start()
    mediaServer.start()

    log.info(" - API Endpoint on http://%s:%d" % (MEDIAHOST, APIPORT))
    log.info(" - Media Endpoint on http://%s:%d" % (MEDIAHOST, MEDIAPORT))
    log.info(" - SSE Events on http://%s:%d/events" % (MEDIAHOST, APIPORT))

    try:
        while(True):
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        running = False
        # Close down threads
        requests.get("http://%s:%d/stopthread" % (MEDIAHOST, APIPORT))
        requests.get("http://%s:%d/stopthread" % (MEDIAHOST, MEDIAPORT))
        log.info("End")

    # threads completely executed
    log.info("Done!")
