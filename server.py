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

import soco # type: ignore


BUILD = "0.0.4"

# Defaults
APIPORT = 8001
MEDIAPORT = 54000
DEBUGMODE = False
MEDIAPATH = "/Volumes/Plex"  # Location of media files
MAXPAYLOAD = 4000            # Reject payload if above this size
DROPPREFIX = "/media"        # Optional - Omit media filename prefix

# Environment config
M3UPATH = os.getenv("M3UPATH", MEDIAPATH) 
MEDIAPATH = os.getenv("MEDIAPATH", MEDIAPATH) 
MEDIAHOST = os.getenv("MEDIAHOST", None) 
DROPPREFIX = os.getenv("DROPPREFIX", DROPPREFIX) 

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

# Global Variables
running = True

# Set up Sonos
sonos = list(soco.discover())[0]
sonos = sonos.group.coordinator
zone = sonos.ip_address

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
        print("MEDIA: url = {} contenttype = {}".format(fpath,ftype))
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
        song = {'id': id, 'length': None, 'title': None, 'path': None, 'album': None, 'artist': None, 'albumartist': None}
        for line in infile:
            line = line.strip()
            if line.startswith("#EXTINF:"):  # song artist - title
                length, title = line.split("#EXTINF:")[1].split(",", 1)
                song['length'] = length
                artist = None
                if " - " in title:
                    artist, title = title.split(" - ")
                song['title'] = title
                song['artist'] = artist
            elif line.startswith("#EXTALB:"): # album
                album = line.split("#EXTALB:")[1]
                song['album'] = album
            elif line.startswith("#EXTART:"): # album artist
                album = line.split("#EXTART:")[1]
                song['albumartist'] = album
            elif line.startswith("#"):
                # Ignore comment lines
                pass
            elif len(line) != 0:
                id = id + 1
                song['path'] = line
                # TODO: Restrict to only MEDIAPATH
                playlist.append(song)
                song = {'id': id, 'length': None, 'title': None, 'path': None, 'album': None, 'artist': None, 'albumartist': None}
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
        print("GET - Path = {}".format(self.path))
        #self.path = requests.utils.unquote(self.path.replace(DROPPREFIX, MEDIAPATH))
        self.path = self.path.replace(DROPPREFIX, "")
        print("    - converted Path = {}".format(self.path))
        try:
            super().do_GET()
        except Exception as e:
            # It's normal to hit some exceptions with Sonos
            print("Exception ignored: {}".format(e))

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

    def do_GET(self):
        global musicqueue, zone, sonos, shuffle, repeat, state, stop
        self.send_response(200)
        message = json.dumps({"Response": "OK"})
        contenttype = 'application/json'
        if self.path == '/speakers':
            # List of Sonos Speakers
            if zone is None:
                sonos = list(soco.discover())[0]
                sonos = sonos.group.coordinator
                zone = sonos.ip_address
            speakers = {}
            for z in soco.discover():
                speakers[z.player_name] = {}
                speakers[z.player_name]["ip"] = z.ip_address
                speakers[z.player_name]["coordinator"] = soco.SoCo(z.ip_address).group.coordinator == soco.SoCo(z.ip_address)
                soco.SoCo("10.0.1.183").group.members
                member = soco.SoCo(z.ip_address) in soco.SoCo(zone).group.members
                speakers[z.player_name]["state"] = member
            message = json.dumps(speakers)
        elif self.path.startswith('/setzone/'):
            zone = self.path.split('/setzone/')[1]
            message = "OK"
        elif self.path == '/stats':
            # Give Internal Stats
            serverstats['ts'] = int(time.time())
            serverstats['mem'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            message = json.dumps(serverstats)
        elif self.path == '/queue':
            # Give Internal Stats
            message = json.dumps(musicqueue)
        elif self.path == '/queue/clear':
            # Clear current queue
            musicqueue = []
        elif self.path== '/play':
            stop = False
            sonos.play()
        elif self.path== '/pause':
            stop = True
            sonos.pause()
        elif self.path== '/stop':
            stop = True
            sonos.stop()
        elif self.path== '/volumeup':
            sonos.group.volume = sonos.group.volume + 1
        elif self.path== '/volumedown':
            sonos.group.volume = sonos.group.volume - 1
        elif self.path== '/next':
            if len(musicqueue) > 0 :
                # Queue up next song
                song = musicqueue.pop(0)
                if repeat:
                    musicqueue.append(song)
                # Play it
                sonos.play_uri(song['path'])
                stop = False
            else:
                 message = json.dumps({"Response": "Playlist Empty"})
        elif self.path== '/prev':
            if repeat and len(musicqueue) > 1:
                   # Queue up next song
                song = musicqueue.pop
                musicqueue.insert(0, song)
                song = musicqueue.pop
                musicqueue.append(song)
                # Play it
                sonos.play_uri(song['path'])
                stop = False
            else:
                if len(musicqueue) <= 1:
                    message = json.dumps({"Response": "Playlist Empty"})
                else:
                    sonos.previous()
        elif self.path== '/state':
            s = {}
            s['state'] = state
            s['zone'] = zone
            s['repeat'] = repeat
            s['shuffle'] = shuffle
            s['volume'] = sonos.group.volume
            message = json.dumps(s)
        elif self.path=='/toggle/repeat':
            repeat = not repeat
        elif self.path=='/toggle/shuffle':
            shuffle = not shuffle
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
        elif self.path== '/current':
            # What is currently playing
            # TODO: title
            sonos = soco.SoCo(zone).group.coordinator
            c = sonos.get_current_track_info().copy()
            state = sonos.get_current_transport_info()['current_transport_state']
            c['state'] = state
            message = json.dumps(c)
        elif self.path == '/queuedepth':
            # Give Internal Stats
            message = json.dumps({"queuedepth": len(musicqueue)})
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
            if shuffle:
                random.shuffle(songs)
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
                musicqueue.append(song)
            message = json.dumps({"Response": "Added {} Songs".format(len(songs))})
        elif self.path.startswith('/playfile/'):
            # Load single song into queue - file in URI
            # TODO: Add other details
            playfile = self.path.split('/playfile/')[1]
            song = {}
            #fn = requests.utils.unquote(self.path.split('/play_file/')[1])
            print("Add PlayFile: {}".format(playfile))
            song['path'] = "http://%s:%d/%s" % (MEDIAHOST, MEDIAPORT, playfile)
            musicqueue.append(song)
            message = json.dumps({"Response": "Added 1 Song"})
        else:
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
                print(self.path)

        # Counts 
        if "Error" in message:
            serverstats['errors'] = serverstats['errors'] + 1
        serverstats['gets'] = serverstats['gets'] + 1

        # Send headers and payload
        self.send_header('Content-type',contenttype)
        self.send_header('Content-Length', str(len(message)))
        self.end_headers()
        self.wfile.write(bytes(message, "utf8"))

# Threads

def jukebox():
    """
    Thread to manage playlist and Sonos Speakers
    """
    global running, musicqueue, state, repeat, shuffle, zone
    coordinator = None

    while running:
        if zone != coordinator:
            # switch to new zone?
            coordinator = zone
            print("Jukebox: switching to {} speakers".format(zone))
            sonos = soco.SoCo(zone).group.coordinator
        # Are there items in the queue?
        if len(musicqueue) > 0 and not stop:
            # is it running?
            state = sonos.get_current_transport_info()['current_transport_state']
            print("STATE: Sonos {}".format(state), end="\r")
            if state != "PLAYING":
                # Queue up next song
                song = musicqueue.pop(0)
                if repeat:
                    musicqueue.append(song)
                # Play it
                sonos.play_uri(song['path'])
                print("")
        time.sleep(5)

def api(port):
    """
    API Server - Thread to listen for commands on port 
    """
    global running
    log.debug("Started API server thread on %d", port)

    with ThreadingHTTPServer(('', port), apihandler) as server:
        try:
            # server.serve_forever()
            while running:
                server.handle_request()
        except:
            print(' CANCEL \n')
    print('\napi Exit')

def media(port):
    """
    Media Server - Thread to listening for requests 
    """
    global running
    log.debug("Started Media server thread on %d", port)

    with ThreadingHTTPServer(('', port), mediahandler) as server:
        try:
            # server.serve_forever()
            while running:
                server.handle_request()
        except:
            print(' CANCEL \n')
    print('\nmedia Exit')

# MAIN Thread
if __name__ == "__main__":
    # creating thread
    apiServer = threading.Thread(target=api, args=(APIPORT,))
    mediaServer = threading.Thread(target=media, args=(MEDIAPORT,))
    jb = threading.Thread(target=jukebox)
    
    print(
        "\nTinySonos Web Based Sonos Controller and Jukebox [v%s - SoCo %s]\n"
        % (BUILD, soco.__version__)
    )

    # start threads
    print("Starting threads...")
    apiServer.start()
    mediaServer.start()
    jb.start()

    print(" - API Endpoint on http://%s:%d" % (MEDIAHOST, APIPORT))
    print(" - Media Endpoint on http://%s:%d" % (MEDIAHOST, MEDIAPORT))

    try:
        while(True):
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        running = False
        # Close down threads
        requests.get("http://%s:%d/stopthread" % (MEDIAHOST, APIPORT))
        requests.get("http://%s:%d/stopthread" % (MEDIAHOST, MEDIAPORT))
        print("End")

    # threads completely executed
    print("Done!")
