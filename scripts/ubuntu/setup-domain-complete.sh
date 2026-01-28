#!/bin/bash
# Complete Domain Setup Script
# ตั้งค่า domain name ทั้งใน Docker container และ nginx บน host

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Domain Name Setup${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Check if domain name provided
if [ -z "$1" ]; then
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo -e "${YELLOW}Usage: $0 <domain-name>${NC}"
    echo -e "${YELLOW}Example: $0 mnp.example.com${NC}"
    echo ""
    echo -e "${CYAN}Current setup uses IP: $SERVER_IP${NC}"
    echo ""
    read -p "Enter domain name (or press Enter to skip): " DOMAIN
    if [ -z "$DOMAIN" ]; then
        echo -e "${YELLOW}Skipping domain setup${NC}"
        exit 0
    fi
else
    DOMAIN=$1
fi

echo ""
echo -e "${CYAN}Setting up domain: ${BLUE}$DOMAIN${NC}"
echo ""

cd "$PROJECT_DIR"

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

# Step 1: Update nginx.conf in frontend container
echo -e "${YELLOW}Step 1: Updating frontend nginx.conf...${NC}"
NGINX_CONF="$PROJECT_DIR/frontend/nginx.conf"

# Backup if not exists
if [ ! -f "${NGINX_CONF}.backup" ]; then
    cp "$NGINX_CONF" "${NGINX_CONF}.backup"
    echo -e "${GREEN}✓ Backed up nginx.conf${NC}"
fi

# Update server_name (support both domain and IP)
sed -i "s/server_name _;/server_name ${DOMAIN} www.${DOMAIN} _;/" "$NGINX_CONF"
echo -e "${GREEN}✓ Updated frontend/nginx.conf${NC}"

# Step 2: Update nginx on host
echo ""
echo -e "${YELLOW}Step 2: Updating nginx on host...${NC}"
NGINX_CONFIG="/etc/nginx/sites-available/mnp"

# Create or update nginx config on host
sudo tee "$NGINX_CONFIG" > /dev/null <<EOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN} _;
    
    # Increase client body size for file uploads
    client_max_body_size 10M;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json application/javascript;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # API proxy - proxy all API endpoints to backend
    location ~ ^/(auth|users|projects|ai|docs|openapi\.json|folders|summary|project-options) {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Increase timeouts for long-running requests
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        # Disable buffering for streaming responses
        proxy_buffering off;
    }
    
    # Frontend static files (proxy to Docker container on port 8080)
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
sudo ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/mnp

# Remove default if exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    sudo rm /etc/nginx/sites-enabled/default
fi

# Test nginx config
if sudo nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
    sudo systemctl reload nginx
    echo -e "${GREEN}✓ Nginx reloaded${NC}"
else
    echo -e "${RED}✗ Nginx configuration has errors${NC}"
    exit 1
fi

# Step 3: Rebuild frontend container
echo ""
echo -e "${YELLOW}Step 3: Rebuilding frontend container...${NC}"
docker compose -f docker-compose.prod.yml build frontend

# Step 4: Restart frontend
echo ""
echo -e "${YELLOW}Step 4: Restarting frontend container...${NC}"
docker compose -f docker-compose.prod.yml restart frontend

sleep 5

# Step 5: Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Domain Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Domain: ${BLUE}$DOMAIN${NC}"
echo -e "${CYAN}Server IP: ${BLUE}$SERVER_IP${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "${CYAN}1. Setup DNS:${NC}"
echo ""
echo -e "${BLUE}   For LAN (Local Network):${NC}"
echo -e "   Add to /etc/hosts on each client machine:"
echo -e "   ${GREEN}$SERVER_IP    $DOMAIN${NC}"
echo -e "   ${GREEN}$SERVER_IP    www.$DOMAIN${NC}"
echo ""
echo -e "${BLUE}   For Internet (Public Domain):${NC}"
echo -e "   Add A records in your DNS provider:"
echo -e "   ${GREEN}$DOMAIN    A    $SERVER_IP${NC}"
echo -e "   ${GREEN}www.$DOMAIN    A    $SERVER_IP${NC}"
echo ""
echo -e "${CYAN}2. Test Access:${NC}"
echo -e "   ${BLUE}http://$DOMAIN${NC}"
echo -e "   ${BLUE}http://$DOMAIN/docs${NC} (Backend API)"
echo ""
echo -e "${CYAN}3. (Optional) Setup SSL/HTTPS:${NC}"
echo -e "   ${BLUE}sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN${NC}"
echo ""
echo -e "${CYAN}Current Access URLs:${NC}"
echo -e "   ${BLUE}Frontend: http://$SERVER_IP${NC}"
echo -e "   ${BLUE}Backend API: http://$SERVER_IP:8000/docs${NC}"
echo -e "   ${BLUE}Domain (after DNS): http://$DOMAIN${NC}"
