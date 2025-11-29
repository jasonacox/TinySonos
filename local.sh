#!/bin/bash
#
# TinySonos Local Development Script
# 
# This script sets up a Python virtual environment and runs the TinySonos server
# locally for testing and development.
#
# See https://github.com/jasonacox/tinysonos
#
# CONFIGURATION:
# Edit the paths below to match your local system setup
#

# ============================================================================
# MEDIA CONFIGURATION
# ============================================================================

# MEDIAPATH: Directory containing your music files
# This is where TinySonos will look for audio files to play
# Examples:
#   macOS:   export MEDIAPATH="/Volumes/Music"
#   Linux:   export MEDIAPATH="/home/user/Music"
#   Windows: export MEDIAPATH="/mnt/c/Music"
export MEDIAPATH="/Volumes/Plex"

# M3UPATH: Directory containing M3U playlist files
# This is where TinySonos will look for .m3u and .m3u8 playlist files
# Can be the same as MEDIAPATH or a separate directory
export M3UPATH="/Volumes/Plex"

# DROPPREFIX: Prefix to remove from M3U file paths
# Used when M3U files contain absolute paths that need to be adjusted for local testing
# Set to the part of the path to strip out so paths inside the container are correct
export DROPPREFIX="/media"

export DEBUGMODE=True

# ============================================================================
# OPTIONAL CONFIGURATION
# ============================================================================

# Uncomment and edit these if you want to customize server behavior:
# export APIPORT=8001          # API server port (default: 8001)
# export MEDIAPORT=54000       # Media server port (default: 54000)
# export DEBUGMODE=True        # Enable debug logging (default: False)
# export SPEAKER="Family Room" # Default Sonos speaker name

# ============================================================================
# SETUP AND RUN
# ============================================================================

echo "Setting up TinySonos virtual environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies from requirements.txt..."
pip install -q -r requirements.txt

# Run the server
echo ""
echo "Starting TinySonos server..."
echo "  Media Path: $MEDIAPATH"
echo "  M3U Path:   $M3UPATH"
echo "  API Server: http://localhost:8001"
echo "  Media Server: http://localhost:54000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 server.py

