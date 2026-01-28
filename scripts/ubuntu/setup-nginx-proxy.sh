#!/bin/bash
# Setup Nginx Proxy on Host
# ตั้งค่า nginx บน host ให้ proxy ไปยัง Docker containers

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
echo -e "${CYAN}Setup Nginx Proxy on Host${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

# Create nginx config
NGINX_CONFIG="/etc/nginx/sites-available/mnp"
echo -e "${YELLOW}Creating Nginx configuration...${NC}"

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
echo -e "${YELLOW}Enabling Nginx site...${NC}"
sudo ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/mnp

# Remove default nginx site if exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    echo -e "${YELLOW}Removing default Nginx site...${NC}"
    sudo rm /etc/nginx/sites-enabled/default
fi

# Test nginx config
echo -e "${YELLOW}Testing Nginx configuration...${NC}"
if sudo nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
    
    # Reload nginx
    echo -e "${YELLOW}Reloading Nginx...${NC}"
    sudo systemctl reload nginx
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Nginx proxy setup completed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${CYAN}Configuration:${NC}"
    echo -e "   Frontend: http://127.0.0.1:8080 → http://$SERVER_IP${NC}"
    echo -e "   Backend: http://127.0.0.1:8000 → http://$SERVER_IP/api/*${NC}"
    echo ""
else
    echo -e "${RED}✗ Nginx configuration has errors${NC}"
    exit 1
fi
