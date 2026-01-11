#!/bin/bash
# Script to setup domain name for the application
# Usage: ./setup-domain.sh <domain-name>
# Example: ./setup-domain.sh mnp.example.com

if [ -z "$1" ]; then
    echo "Usage: $0 <domain-name>"
    echo "Example: $0 mnp.example.com"
    exit 1
fi

DOMAIN=$1
NGINX_CONF="frontend/nginx.conf"

echo "🔧 Setting up domain: $DOMAIN"

# Backup nginx.conf
if [ ! -f "${NGINX_CONF}.backup" ]; then
    cp "$NGINX_CONF" "${NGINX_CONF}.backup"
    echo "✅ Backed up nginx.conf to ${NGINX_CONF}.backup"
fi

# Update nginx.conf
sed -i "s/server_name _;/server_name ${DOMAIN} www.${DOMAIN} _;/" "$NGINX_CONF"
echo "✅ Updated nginx.conf with domain: $DOMAIN"

# Rebuild frontend
echo "🔨 Rebuilding frontend container..."
docker compose -f docker-compose.prod.yml build frontend

# Restart frontend
echo "🔄 Restarting frontend container..."
docker compose -f docker-compose.prod.yml up -d frontend

echo ""
echo "✅ Domain setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Add to /etc/hosts (on each client machine):"
echo "   <server-ip>    $DOMAIN"
echo "   <server-ip>    www.$DOMAIN"
echo ""
echo "2. Or configure DNS server to point $DOMAIN to <server-ip>"
echo ""
echo "3. Test access: http://$DOMAIN"
echo ""
echo "💡 To revert changes:"
echo "   cp ${NGINX_CONF}.backup $NGINX_CONF"
echo "   docker compose -f docker-compose.prod.yml build frontend"
echo "   docker compose -f docker-compose.prod.yml up -d frontend"

