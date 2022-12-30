# PlexExportM3U - Plex Playlist Exporter
# -*- coding: utf-8 -*-
"""
Export Plex playlist into M3U format (*.m3u8 files)

Author: Jason A. Cox
Date: December 11, 2022
For more information see https://github.com/jasonacox/tinysonos

Description
    This tool connects to your Plex server and exports all of the
    audio playlists to m3u8 files. 

    There are two arguments required:
        python3 PlexExportM3U.py <Plex_Host> <Plex_Token> <Dest_Dir>

        Plex_Host - Base URL for Plex Server
        Plex_Token - see https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/
        Dest_Dir - Location to store m3u8 files

Requirements:
    * plexapi (pip install plexapi)

Credits:
    * This is based on the great work done by evolve700 at
    https://github.com/evolve700/PlexPlaylistExport

"""

import requests
import sys
import plexapi
from plexapi.server import PlexServer

BUILD = "0.0.1"

def export_playlists(host, token, dest="."):
    """ Export all audio playlists on the given Plex server
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

    print('Getting playlists... ', end='')
    playlists = plex.playlists()

    for playlist in playlists:
        if (playlist.playlistType == 'audio'):
            print('Exporting %s' % playlist.title)
            m3u = open('%s/%s.%s' % (dest, playlist.title, "m3u8"), 'w', encoding="utf-8")
            m3u.write('#EXTM3U\n')
            m3u.write('#TinySonos - PlexExportM3U [{}] - https://github.com/jasonacox/TinySonos/tree/main/tools\n'.format(BUILD))
            m3u.write('#{"playlistType": "%s", "title": "%s", "leafCount": "%s",  "server": "%s", "created": "%s"}\n' %
                (playlist.playlistType, playlist.title,
                playlist.leafCount, host,
                playlist.updatedAt.strftime("%m/%d/%Y, %H:%M:%S"))
            )
            m3u.write('#PLAYLIST:%s\n' % playlist.title)
            m3u.write('\n')
            # export each song in playlist
            songs = playlist.items()
            print(' - %s songs' % playlist.leafCount)
            for song in songs:  
                # song and title details  
                media = song.media[0]
                seconds = int(song.duration / 1000)
                title = song.title        
                album = song.parentTitle
                artist = song.originalTitle
                albumArtist = song.grandparentTitle
                if artist == None:
                    artist = albumArtist     
                m3u.write('#PLEX ALBUM=%s,SONG=%s\n' % (song.album().key.split('metadata/')[1],song.key.split('metadata/')[1])) 
                m3u.write('#EXTALB:%s\n' % album)
                m3u.write('#EXTART:%s\n' % albumArtist)  
                # media file details
                parts = media.parts
                for part in parts:
                    m3u.write('#EXTINF:%s,%s - %s\n' % (seconds, artist, title))
                    m3u.write('%s\n' % part.file)
                    m3u.write('\n')
            # close file
            m3u.close()

print("PlexExportM3U [{}] - Export M3U Playlists from Plex")

print(len(sys.argv))

if len(sys.argv) < 3:
    print("\nUsage:  {} <Plex_Host> <Plex_Token> <Dest_Dir>".format(sys.argv[0]))
    print("")
    print("    Plex_Host - Base URL for Plex Server")
    print("    Plex_Token - see https://github.com/jasonacox/TinySonos/tree/main/tools")
    print("    Dest_Dir - Location to store m3u8 files")
    print("")
else:
    host = sys.argv[1]
    token = sys.argv[2]
    if len(sys.argv) > 3:
        dest = sys.argv[3]
    else:
        dest = "."

    print("Exporting Plex Playlists to {}".format(dest))
    print(" - Host: {}".format(host))
    export_playlists(host,token,dest)

