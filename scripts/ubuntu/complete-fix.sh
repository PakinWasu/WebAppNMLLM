#!/bin/bash
# Complete Fix Script - แก้ไขทุกอย่างให้ใช้งานได้ครบถ้วน
# Run with: sudo bash scripts/ubuntu/complete-fix.sh

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
echo -e "${CYAN}Complete Fix - แก้ไขทุกอย่างให้ใช้งานได้${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

cd "$PROJECT_DIR"

# Step 1: Check Docker containers
echo -e "${YELLOW}Step 1: Checking Docker containers...${NC}"
if command -v docker >/dev/null 2>&1; then
    if docker ps >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Docker is accessible${NC}"
        docker compose -f docker-compose.prod.yml ps
    else
        echo -e "${RED}✗ Docker is not accessible${NC}"
        echo -e "${YELLOW}Please run: newgrp docker${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Docker is not installed${NC}"
    exit 1
fi

# Step 2: Ensure containers are running
echo ""
echo -e "${YELLOW}Step 2: Ensuring containers are running...${NC}"
docker compose -f docker-compose.prod.yml up -d
sleep 5

# Step 3: Setup nginx on host
echo ""
echo -e "${YELLOW}Step 3: Setting up nginx on host...${NC}"

NGINX_CONFIG="/etc/nginx/sites-available/mnp"

# Create nginx config
sudo tee "$NGINX_CONFIG" > /dev/null <<'EOF'
server {
    listen 80;
    server_name _ nmp.local www.nmp.local;
    
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

# Test and reload nginx
if sudo nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
    sudo systemctl reload nginx
    echo -e "${GREEN}✓ Nginx reloaded${NC}"
else
    echo -e "${RED}✗ Nginx configuration has errors${NC}"
    exit 1
fi

# Step 4: Wait for services
echo ""
echo -e "${YELLOW}Step 4: Waiting for services to be ready...${NC}"
sleep 5

# Step 5: Test everything
echo ""
echo -e "${CYAN}Step 5: Testing all endpoints...${NC}"

SERVER_IP=$(hostname -I | awk '{print $1}')

# Test frontend (port 8080)
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 | grep -q "200"; then
    echo -e "${GREEN}✓ Frontend (port 8080) is accessible${NC}"
else
    echo -e "${RED}✗ Frontend (port 8080) is not accessible${NC}"
fi

# Test frontend via nginx (port 80)
if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200"; then
    echo -e "${GREEN}✓ Frontend via nginx (port 80) is accessible${NC}"
else
    echo -e "${RED}✗ Frontend via nginx (port 80) is not accessible${NC}"
fi

# Test backend API
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs | grep -q "200"; then
    echo -e "${GREEN}✓ Backend API (port 8000) is accessible${NC}"
else
    echo -e "${RED}✗ Backend API (port 8000) is not accessible${NC}"
fi

# Test API via proxy
if curl -s -o /dev/null -w "%{http_code}" http://localhost/docs | grep -q "200"; then
    echo -e "${GREEN}✓ Backend API via proxy is accessible${NC}"
else
    echo -e "${YELLOW}⚠ Backend API via proxy may not be accessible${NC}"
fi

# Test assets
ASSET_FILE=$(curl -s http://localhost:8080 | grep -o 'src="/assets/[^"]*"' | head -1 | sed 's/.*src="\([^"]*\)".*/\1/')
if [ -n "$ASSET_FILE" ]; then
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080$ASSET_FILE" | grep -q "200"; then
        echo -e "${GREEN}✓ Assets are accessible${NC}"
    else
        echo -e "${RED}✗ Assets are not accessible${NC}"
    fi
    
    # Test assets via nginx
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost$ASSET_FILE" | grep -q "200"; then
        echo -e "${GREEN}✓ Assets via nginx are accessible${NC}"
    else
        echo -e "${RED}✗ Assets via nginx are not accessible${NC}"
    fi
fi

# Step 6: Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Access URLs:${NC}"
echo -e "   ${BLUE}Frontend: http://$SERVER_IP${NC}"
echo -e "   ${BLUE}Frontend (direct): http://$SERVER_IP:8080${NC}"
echo -e "   ${BLUE}Backend API: http://$SERVER_IP:8000/docs${NC}"
echo -e "   ${BLUE}Backend API (via proxy): http://$SERVER_IP/docs${NC}"
echo ""
echo -e "${CYAN}Domain (if DNS configured):${NC}"
echo -e "   ${BLUE}Frontend: http://nmp.local${NC}"
echo ""
echo -e "${CYAN}Default Login:${NC}"
echo -e "   ${BLUE}Username: admin${NC}"
echo -e "   ${BLUE}Password: admin123${NC}"
echo -e "   ${RED}⚠️  Change password immediately!${NC}"
echo ""
echo -e "${YELLOW}If you see white screen:${NC}"
echo -e "   1. Clear browser cache (Ctrl+Shift+R)"
echo -e "   2. Try incognito/private mode"
echo -e "   3. Check browser console (F12) for errors"
echo ""
