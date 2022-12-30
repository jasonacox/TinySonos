# PlexExportM3U - Plex Playlist Exporter
# -*- coding: utf-8 -*-
"""
Export Plex Music Database into JSON File

Author: Jason A. Cox
Date: December 29, 2022
For more information see https://github.com/jasonacox/tinysonos

Description
    This tool connects to your Plex Music Database and Album Art

    There are two arguments required:
        python3 PlexExportSongs.py <Plex_Host> <Plex_Token> <Dest_Dir>

        Plex_Host - Base URL for Plex Server
        Plex_Token - see https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/
        Dest_Dir - Location to store m3u8 files

Requirements:
    * plexapi (pip install plexapi)

"""

import requests
import sys
import plexapi
from plexapi.server import PlexServer
import urllib.request
import os
import json

BUILD = "0.0.1"

def export_songs(host, token, dest="."):
    """ Export all song library on the given Plex server
    """
    if dest.endswith("/"):
        dest = dest[:-1]
    print('Connecting to plex...', end='')
    try:
        plex = PlexServer(host, token)
    except (plexapi.exceptions.Unauthorized, requests.exceptions.ConnectionError):
        print(' failed')
        return
    print(' done')

    print('Getting albums... ', end='')
    db = dict()
    idx_album = dict()
    idx_song = dict()
    idx_artist = dict()
    idx_added = dict()
    idx_songkey = dict()
    m = plex.library.section('Music')

    allalbums = m.albums() # all albums
    #allalbums = m.recentlyAddedAlbums() # only recent 

    # spot to store album art
    path = "%s/album-art" % dest
    isExist = os.path.exists(path)
    if not isExist:
        os.makedirs(path)

    # loop through every album
    uid = 0
    for album in allalbums:
        uid = int(album.key.split("metadata/")[1])
        # print (album.key)
        db[uid] = dict()
        db[uid]["title"] = album.title
        if album.title not in idx_album:
            idx_album[album.title] = [uid]
        else:
            idx_album[album.title].append(uid)
        #db[uid]["thumbUrl"] = album.thumbUrl
        thumbUrl = album.thumbUrl
        localfile = "%s/album-art/%d.png" % (dest,uid)
        # print("  - copy {}".format(thumbUrl))
        if thumbUrl:
            response = urllib.request.urlretrieve(thumbUrl, localfile)
            db[uid]["thumbfile"] = localfile
        else:
            db[uid]["thumbfile"] = None
        db[uid]["artist"] = album.artist().title
        db[uid]["added"] = album.addedAt.timestamp()
        idx_added[album.addedAt.timestamp()] = uid
        index = 0
        indexarray = [0]
        tracks = dict()
        for track in album.tracks():
            if track.index:
                index = int(track.index)
            else:
                index = max(indexarray) + 1
            indexarray.append(index)
            tracks[index] = dict()
            tracks[index]["song"] = track.title
            tracks[index]["path"] = track.locations
            key = track.key.split('metadata/')[1]
            tracks[index]["key"] = key
            artist = track.artist().title
            tracks[index]["artist"] = artist
            if track.title not in idx_song:
                idx_song[track.title] = [uid]
            elif uid not in idx_song[track.title]:
                idx_song[track.title].append(uid)
            if artist not in idx_artist:
                idx_artist[artist] = [uid]
            elif uid not in idx_artist[artist]:
                idx_artist[artist].append(uid)
            if key not in idx_songkey:
                idx_songkey[key] = [uid]
            elif uid not in idx_songkey[key]:
                idx_songkey[key].append(uid)
        db[uid]["tracks"] = tracks
        print("{} - {}- {} - {} tracks - {}".format(uid,album.title,album.artist().title,len(tracks),track.locations))

    # write the database
    dbfile = "%s/db.json" % dest
    with open(dbfile, 'w') as fp:
        json.dump(db, fp)
    dbfile = "%s/db.albums.json" % dest
    with open(dbfile, 'w') as fp:
        json.dump(idx_album, fp)
    dbfile = "%s/db.songs.json" % dest
    with open(dbfile, 'w') as fp:
        json.dump(idx_song, fp)
    dbfile = "%s/db.songkey.json" % dest
    with open(dbfile, 'w') as fp:
        json.dump(idx_songkey, fp)
    dbfile = "%s/db.artists.json" % dest
    with open(dbfile, 'w') as fp:
        json.dump(idx_artist, fp)
    temp = dict(sorted(idx_added.items(),reverse=True))
    dbfile = "%s/db.added.json" % dest
    with open(dbfile, 'w') as fp:
        json.dump(temp, fp)
    

print("PlexExportSongs [{}] - Export Music Database from Plex")

print(len(sys.argv))

if len(sys.argv) < 3:
    print("\nUsage:  {} <Plex_Host> <Plex_Token> <Dest_Dir>".format(sys.argv[0]))
    print("")
    print("    Plex_Host - Base URL for Plex Server")
    print("    Plex_Token - see https://github.com/jasonacox/TinySonos/tree/main/tools")
    print("    Dest_Dir - Location to store database files")
    print("")
else:
    host = sys.argv[1]
    token = sys.argv[2]
    if len(sys.argv) > 3:
        dest = sys.argv[3]
    else:
        dest = "."

    print("Exporting Plex Music Database to {}".format(dest))
    print(" - Host: {}".format(host))
    export_songs(host,token,dest)

