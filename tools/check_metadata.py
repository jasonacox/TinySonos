#!/usr/bin/env python3
"""
Audio Metadata Checker for TinySonos

This script checks audio files for embedded metadata including album art.
It's useful for verifying that your music files have proper tags and artwork
that will be displayed by Sonos players and the TinySonos UI.

Supported Formats:
    - MP3 (ID3 tags)
    - M4A/MP4 (iTunes/Apple tags)
    - FLAC
    - And other formats supported by mutagen

What it checks:
    - Title, Artist, Album, Date, Genre metadata
    - Embedded album artwork (presence, format, size)
    - File format detection

Usage:
    Check a single file:
        python3 check_metadata.py /path/to/song.mp3
    
    Check multiple files:
        python3 check_metadata.py /path/to/album/*.mp3
    
    Check all files in a directory:
        python3 check_metadata.py /path/to/music/**/*.m4a

Requirements:
    pip3 install mutagen

Author: TinySonos Project
Date: November 2025
"""

import sys
from mutagen import File
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

def check_metadata(filepath):
    """
    Check metadata and album art in audio file.
    
    Args:
        filepath: Path to audio file to analyze
        
    Displays:
        - File type and format
        - Metadata tags (title, artist, album, date, genre)
        - Album art information (if present)
        - Recommendations if album art is missing
    """
    print(f"\n{'='*60}")
    print(f"Checking: {filepath}")
    print(f"{'='*60}\n")
    
    try:
        # Use mutagen to auto-detect file type
        audio = File(filepath)
        
        if audio is None:
            print("❌ Could not read file or unsupported format")
            return
        
        print(f"File Type: {type(audio).__name__}")
        print(f"\nMetadata Tags:")
        print(f"{'-'*60}")
        
        # Get metadata based on file type
        if isinstance(audio, MP4):
            # MP4/M4A uses different tag names
            title = audio.tags.get('\xa9nam', ['(not set)'])[0] if '\xa9nam' in audio.tags else '(not set)'
            artist = audio.tags.get('\xa9ART', ['(not set)'])[0] if '\xa9ART' in audio.tags else '(not set)'
            album = audio.tags.get('\xa9alb', ['(not set)'])[0] if '\xa9alb' in audio.tags else '(not set)'
            date = audio.tags.get('\xa9day', ['(not set)'])[0] if '\xa9day' in audio.tags else '(not set)'
            genre = audio.tags.get('\xa9gen', ['(not set)'])[0] if '\xa9gen' in audio.tags else '(not set)'
            
            print(f"  {'Title':<12}: {title}")
            print(f"  {'Artist':<12}: {artist}")
            print(f"  {'Album':<12}: {album}")
            print(f"  {'Date':<12}: {date}")
            print(f"  {'Genre':<12}: {genre}")
        else:
            # MP3, FLAC, and other formats use standard tags
            tags_to_check = ['title', 'artist', 'album', 'date', 'genre']
            
            for tag in tags_to_check:
                value = audio.get(tag, ['(not set)'])[0] if hasattr(audio.get(tag, None), '__iter__') else audio.get(tag, '(not set)')
                print(f"  {tag.capitalize():<12}: {value}")
        
        # Check for album art
        print(f"\n{'='*60}")
        print("Album Art Check:")
        print(f"{'='*60}")
        
        has_art = False
        art_info = []
        
        # MP3 (ID3 tags)
        if isinstance(audio, MP3):
            for key in audio.tags.keys():
                if key.startswith('APIC'):
                    pic = audio.tags[key]
                    has_art = True
                    art_info.append({
                        'type': pic.type,
                        'mime': pic.mime,
                        'desc': pic.desc,
                        'size': len(pic.data)
                    })
        
        # FLAC
        elif isinstance(audio, FLAC):
            if audio.pictures:
                has_art = True
                for pic in audio.pictures:
                    art_info.append({
                        'type': pic.type,
                        'mime': pic.mime,
                        'desc': pic.desc,
                        'size': len(pic.data)
                    })
        
        # MP4/M4A
        elif isinstance(audio, MP4):
            if 'covr' in audio.tags:
                has_art = True
                for cover in audio.tags['covr']:
                    # Determine image format
                    mime_type = 'image/unknown'
                    if hasattr(cover, 'imageformat'):
                        # MP4Cover.FORMAT_JPEG = 13, FORMAT_PNG = 14
                        if cover.imageformat == 13:
                            mime_type = 'image/jpeg'
                        elif cover.imageformat == 14:
                            mime_type = 'image/png'
                    art_info.append({
                        'type': 'Cover',
                        'mime': mime_type,
                        'size': len(cover)
                    })
        
        if has_art:
            print(f"✅ Album art FOUND! ({len(art_info)} image(s))")
            for i, art in enumerate(art_info, 1):
                print(f"\n  Image {i}:")
                print(f"    Type: {art.get('type', 'Unknown')}")
                print(f"    MIME: {art.get('mime', 'Unknown')}")
                if 'desc' in art:
                    print(f"    Description: {art['desc']}")
                print(f"    Size: {art['size']:,} bytes ({art['size']/1024:.1f} KB)")
        else:
            print("❌ No album art found in file")
            print("\n💡 Tip: You can add album art using tools like:")
            print("   - MusicBrainz Picard")
            print("   - Mp3tag")
            print("   - Kid3")
        
        print(f"\n{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 check_metadata.py <audio_file>")
        print("\nExample:")
        print("  python3 check_metadata.py /media/Music/Artist/Album/song.mp3")
        print("\nOr check multiple files:")
        print("  python3 check_metadata.py /media/Music/Artist/Album/*.mp3")
        sys.exit(1)
    
    # Check all files provided
    for filepath in sys.argv[1:]:
        check_metadata(filepath)
