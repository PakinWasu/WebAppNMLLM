#!/bin/bash
# Script to add mnp.local to Linux/Mac hosts file
# Usage: ./setup-hosts-linux.sh [server-ip]
# Example: ./setup-hosts-linux.sh 10.4.15.53

SERVER_IP=${1:-"10.4.15.53"}
DOMAIN="mnp.local"
HOSTS_FILE="/etc/hosts"

echo "========================================"
echo "Setup $DOMAIN in hosts file"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    echo "Usage: sudo ./setup-hosts-linux.sh [$SERVER_IP]"
    exit 1
fi

# Check if entry already exists
if grep -q "$DOMAIN" "$HOSTS_FILE"; then
    echo "Entry already exists in hosts file:"
    grep "$DOMAIN" "$HOSTS_FILE"
    echo ""
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "No changes made."
        exit 0
    fi
    # Remove old entry
    sed -i "/$DOMAIN/d" "$HOSTS_FILE"
fi

# Add new entry
echo "Adding entry to hosts file..."
echo "$SERVER_IP    $DOMAIN" >> "$HOSTS_FILE"
echo "$SERVER_IP    www.$DOMAIN" >> "$HOSTS_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully added to hosts file!"
    echo ""
    echo "Flushing DNS cache..."
    
    # Try different methods based on system
    if command -v systemd-resolve &> /dev/null; then
        systemd-resolve --flush-caches 2>/dev/null || true
    fi
    if command -v resolvectl &> /dev/null; then
        resolvectl flush-caches 2>/dev/null || true
    fi
    if command -v dscacheutil &> /dev/null; then
        dscacheutil -flushcache 2>/dev/null || true
        killall -HUP mDNSResponder 2>/dev/null || true
    fi
    
    echo "✅ DNS cache flushed!"
    echo ""
    echo "You can now access: http://$DOMAIN"
    echo ""
    echo "To verify:"
    echo "  ping $DOMAIN"
    echo "  nslookup $DOMAIN"
else
    echo ""
    echo "❌ Error: Could not write to hosts file"
    exit 1
fi

