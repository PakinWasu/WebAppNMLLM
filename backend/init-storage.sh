#!/bin/bash
# Initialize storage directory with proper permissions
# This script works on both Linux/Ubuntu and Windows (WSL/Docker)

STORAGE_DIR="/app/storage"

# Create storage directory
mkdir -p "$STORAGE_DIR"

# Detect OS type
if [ -f /proc/version ] && grep -qi microsoft /proc/version; then
    # Running on Windows (WSL)
    echo "Detected Windows/WSL environment"
    # On Windows, permissions are handled differently
    chmod -R 777 "$STORAGE_DIR" 2>/dev/null || true
elif [ "$(uname)" = "Linux" ]; then
    # Running on Linux/Ubuntu
    echo "Detected Linux/Ubuntu environment"
    # Set full permissions (777) for Docker compatibility
    chmod -R 777 "$STORAGE_DIR" 2>/dev/null || true
    # Try to set ownership to current user (may fail in Docker)
    if [ -n "$(id -u 2>/dev/null)" ] && [ -n "$(id -g 2>/dev/null)" ]; then
        chown -R $(id -u):$(id -g) "$STORAGE_DIR" 2>/dev/null || true
    fi
else
    # Unknown OS, just try to set permissions
    echo "Unknown OS, attempting to set permissions"
    chmod -R 777 "$STORAGE_DIR" 2>/dev/null || true
fi

# Ensure all subdirectories have proper permissions
find "$STORAGE_DIR" -type d -exec chmod 777 {} \; 2>/dev/null || true
find "$STORAGE_DIR" -type f -exec chmod 666 {} \; 2>/dev/null || true

echo "✅ Storage directory initialized: $STORAGE_DIR"
echo "   Permissions set for cross-platform compatibility"

