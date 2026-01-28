#!/bin/bash
# Nginx Setup Script for Ubuntu Server
# สคริปต์สำหรับตั้งค่า Nginx เป็น reverse proxy บน host

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Nginx Reverse Proxy Setup${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Check if nginx is installed
if ! command -v nginx >/dev/null 2>&1; then
    echo -e "${YELLOW}Installing Nginx...${NC}"
    sudo apt update
    sudo apt install -y nginx
fi

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

# Ask for domain name
read -p "Enter domain name (or press Enter to use IP: $SERVER_IP): " DOMAIN_NAME
if [ -z "$DOMAIN_NAME" ]; then
    DOMAIN_NAME="_"
fi

# Ask for frontend port (default 8080)
read -p "Enter frontend container port (default: 8080): " FRONTEND_PORT
FRONTEND_PORT=${FRONTEND_PORT:-8080}

# Ask for backend port (default 8000)
read -p "Enter backend container port (default: 8000): " BACKEND_PORT
BACKEND_PORT=${BACKEND_PORT:-8000}

# Create nginx config
NGINX_CONFIG="/etc/nginx/sites-available/mnp"
echo -e "${YELLOW}Creating Nginx configuration...${NC}"

sudo tee "$NGINX_CONFIG" > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;
    
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
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
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
    
    # Frontend static files
    location / {
        proxy_pass http://127.0.0.1:$FRONTEND_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
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
    echo -e "${GREEN}Nginx setup completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${CYAN}Configuration:${NC}"
    echo -e "   Config file: ${BLUE}$NGINX_CONFIG${NC}"
    echo -e "   Domain: ${BLUE}$DOMAIN_NAME${NC}"
    echo -e "   Frontend port: ${BLUE}$FRONTEND_PORT${NC}"
    echo -e "   Backend port: ${BLUE}$BACKEND_PORT${NC}"
    echo ""
    echo -e "${CYAN}Useful commands:${NC}"
    echo -e "   Edit config: ${BLUE}sudo nano $NGINX_CONFIG${NC}"
    echo -e "   Test config: ${BLUE}sudo nginx -t${NC}"
    echo -e "   Reload: ${BLUE}sudo systemctl reload nginx${NC}"
    echo -e "   Status: ${BLUE}sudo systemctl status nginx${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  Important:${NC}"
    echo -e "   Make sure docker-compose.prod.yml maps:"
    echo -e "   - Frontend to port $FRONTEND_PORT:80"
    echo -e "   - Backend to port $BACKEND_PORT:8000"
    echo ""
else
    echo -e "${RED}✗ Nginx configuration has errors${NC}"
    echo -e "${YELLOW}Please fix the errors and try again${NC}"
    exit 1
fi
