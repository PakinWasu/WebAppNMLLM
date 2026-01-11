#!/bin/bash
# Script to fix storage permissions for Ubuntu Server
# This script should be run on the host (Ubuntu Server) to fix permissions
# Usage: ./fix-storage-permissions.sh

STORAGE_DIR="./storage"

echo "🔧 Fixing storage permissions for Ubuntu Server..."

# Check if storage directory exists
if [ ! -d "$STORAGE_DIR" ]; then
    echo "Creating storage directory..."
    mkdir -p "$STORAGE_DIR"
fi

# Set permissions recursively
echo "Setting permissions to 777 for directories..."
find "$STORAGE_DIR" -type d -exec chmod 777 {} \; 2>/dev/null || true

echo "Setting permissions to 666 for files..."
find "$STORAGE_DIR" -type f -exec chmod 666 {} \; 2>/dev/null || true

# Set ownership to current user (optional, may require sudo)
if [ "$EUID" -eq 0 ]; then
    echo "Running as root, setting ownership..."
    # If running as root, set ownership to docker user if exists
    if id "docker" &>/dev/null; then
        chown -R docker:docker "$STORAGE_DIR" 2>/dev/null || true
    fi
else
    echo "Setting ownership to current user: $(whoami)"
    chown -R $(whoami):$(whoami) "$STORAGE_DIR" 2>/dev/null || true
fi

# Ensure base directory has correct permissions
chmod 777 "$STORAGE_DIR" 2>/dev/null || true

echo "✅ Storage permissions fixed!"
echo "   Directory: $STORAGE_DIR"
echo ""
echo "💡 If you still have permission issues, try:"
echo "   sudo chown -R $(whoami):$(whoami) $STORAGE_DIR"
echo "   sudo chmod -R 777 $STORAGE_DIR"

