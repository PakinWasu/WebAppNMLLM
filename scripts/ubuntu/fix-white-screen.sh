#!/bin/bash
# Fix White Screen Issue
# แก้ไขปัญหาจอขาวที่เกิดจาก nginx บน host ไม่ได้ proxy ไปยัง frontend container

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
echo -e "${CYAN}Fix White Screen Issue${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

cd "$PROJECT_DIR"

# Check nginx on host
if ! systemctl is-active --quiet nginx 2>/dev/null; then
    echo -e "${YELLOW}Nginx on host is not running${NC}"
    echo -e "${YELLOW}Starting nginx...${NC}"
    sudo systemctl start nginx
fi

# Create nginx config
NGINX_CONFIG="/etc/nginx/sites-available/mnp"
echo -e "${YELLOW}Creating/updating nginx configuration...${NC}"

sudo tee "$NGINX_CONFIG" > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;
    
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
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
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
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
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

# Check frontend container
echo ""
echo -e "${YELLOW}Checking frontend container...${NC}"
if docker compose -f docker-compose.prod.yml ps frontend | grep -q "healthy\|Up"; then
    echo -e "${GREEN}✓ Frontend container is running${NC}"
else
    echo -e "${YELLOW}⚠ Frontend container may not be running${NC}"
    echo -e "${YELLOW}Starting frontend container...${NC}"
    docker compose -f docker-compose.prod.yml up -d frontend
    sleep 5
fi

# Test access
echo ""
echo -e "${CYAN}Testing access...${NC}"
sleep 2

if curl -s http://localhost >/dev/null 2>&1; then
    HTML_CONTENT=$(curl -s http://localhost | grep -o "<!DOCTYPE html" || echo "")
    if [ -n "$HTML_CONTENT" ]; then
        echo -e "${GREEN}✓ Frontend is accessible${NC}"
    else
        echo -e "${YELLOW}⚠ Frontend returns content but may have issues${NC}"
    fi
else
    echo -e "${RED}✗ Cannot access frontend${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Fix Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
SERVER_IP=$(hostname -I | awk '{print $1}')
echo -e "${CYAN}Access URLs:${NC}"
echo -e "   ${BLUE}http://$SERVER_IP${NC}"
echo -e "   ${BLUE}http://nmp.local${NC} (if DNS configured)"
echo ""
echo -e "${YELLOW}If still seeing white screen:${NC}"
echo -e "   1. Clear browser cache (Ctrl+Shift+R)"
echo -e "   2. Check browser console (F12) for errors"
echo -e "   3. Verify assets are loading: http://$SERVER_IP/assets/"
