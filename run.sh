#!/bin/bash
#
# TinySonos Docker Run Script
#
# This script runs TinySonos in a Docker container with proper network access
# and volume mounting for your music library.
#
# See https://github.com/jasonacox/tinysonos
#
# CONFIGURATION:
# Edit the paths and settings below to match your system setup
#

# ============================================================================
# VOLUME CONFIGURATION
# ============================================================================

# Local path to your music directory (on the host machine)
# This directory will be mounted into the container as /media
# Examples:
#   "/mnt/music"     - Linux with mounted drive
#   "/media/library" - Standard Linux media path
#   "/Volumes/Music" - macOS external drive
MUSIC_DIR="/media"

# ============================================================================
# ENVIRONMENT VARIABLES
# ============================================================================

# M3UPATH: Path inside container where M3U playlists are located
M3U_PATH="/media"

# MEDIAPATH: Path inside container where music files are located  
MEDIA_PATH="/media"

# DROPPREFIX: Prefix to remove from M3U file paths (used when M3U files
# contain absolute paths that need to be adjusted for the container)
DROP_PREFIX="/media"

# ============================================================================
# OPTIONAL CONFIGURATION
# ============================================================================

# Uncomment and edit these if you want to customize server behavior:
# API_PORT=8001           # API server port (default: 8001)
# MEDIA_PORT=54000        # Media server port (default: 54000)
# DEBUG_MODE=True         # Enable debug logging (default: False)
# SPEAKER="Family Room"   # Default Sonos speaker name

# ============================================================================
# DOCKER RUN COMMAND
# ============================================================================

echo "Starting TinySonos Docker container..."
echo "  Music Directory: $MUSIC_DIR"
echo "  Container Path:  $MEDIA_PATH"
echo "  API Server:      http://localhost:8001"
echo "  Media Server:    http://localhost:54000"
echo ""

docker run \
  -d \
  --network host \
  -e M3UPATH="$M3U_PATH" \
  -e MEDIAPATH="$MEDIA_PATH" \
  -e DROPPREFIX="$DROP_PREFIX" \
  -v "$MUSIC_DIR":"$MEDIA_PATH":ro \
  --name tinysonos \
  --user ${UID} \
  --restart unless-stopped \
  jasonacox/tinysonos

# Check if container started successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "✓ TinySonos container started successfully!"
    echo ""
    echo "Usage:"
    echo "  View logs:    docker logs -f tinysonos"
    echo "  Stop:         docker stop tinysonos"
    echo "  Restart:      docker restart tinysonos"
    echo "  Remove:       docker rm -f tinysonos"
    echo ""
    echo "Access the web interface at: http://localhost:8001"
else
    echo ""
    echo "✗ Failed to start TinySonos container"
    echo "  Check if a container named 'tinysonos' already exists:"
    echo "  docker ps -a | grep tinysonos"
    echo ""
    echo "  If it exists, remove it first:"
    echo "  docker rm -f tinysonos"
fi
