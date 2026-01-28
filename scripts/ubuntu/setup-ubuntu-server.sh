#!/bin/bash
# Setup Script for Ubuntu Server
# สคริปต์สำหรับติดตั้งและตั้งค่าโปรเจคบน Ubuntu Server

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Ubuntu Server Setup Script${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Error: Please do not run as root. Run as regular user with sudo privileges.${NC}"
   exit 1
fi

# Function to print section header
print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to check command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Update system
print_section "1. Updating System Packages"
echo -e "${YELLOW}Updating package list...${NC}"
sudo apt update
sudo apt upgrade -y
echo -e "${GREEN}✓ System updated${NC}"

# 2. Install required packages
print_section "2. Installing Required Packages"
REQUIRED_PACKAGES=(
    "curl"
    "wget"
    "git"
    "ufw"
    "nginx"
    "certbot"
    "python3-certbot-nginx"
)

for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! dpkg -l | grep -q "^ii  $package "; then
        echo -e "${YELLOW}Installing $package...${NC}"
        sudo apt install -y "$package"
    else
        echo -e "${GREEN}✓ $package already installed${NC}"
    fi
done

# 3. Install Docker
print_section "3. Installing Docker"
if ! command_exists docker; then
    echo -e "${YELLOW}Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sudo sh /tmp/get-docker.sh
    rm /tmp/get-docker.sh
    
    # Add user to docker group
    sudo usermod -aG docker $USER
    echo -e "${YELLOW}Added $USER to docker group${NC}"
    echo -e "${YELLOW}Activating docker group...${NC}"
    # Try to activate group immediately (may not work in all cases)
    newgrp docker <<EOF || true
EOF
    echo -e "${YELLOW}Note: If docker commands fail, you may need to logout and login again${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# 4. Install Docker Compose
print_section "4. Installing Docker Compose"
# Check if docker compose plugin exists
if ! docker compose version >/dev/null 2>&1; then
    echo -e "${YELLOW}Installing Docker Compose...${NC}"
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    # Also install docker compose plugin (V2)
    DOCKER_COMPOSE_PLUGIN_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    mkdir -p ~/.docker/cli-plugins
    curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_PLUGIN_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o ~/.docker/cli-plugins/docker-compose
    chmod +x ~/.docker/cli-plugins/docker-compose
    echo -e "${GREEN}✓ Docker Compose installed${NC}"
else
    echo -e "${GREEN}✓ Docker Compose already installed${NC}"
fi

# 5. Configure Firewall
print_section "5. Configuring Firewall"
echo -e "${YELLOW}Configuring UFW firewall...${NC}"

# Allow SSH (important!)
sudo ufw allow 22/tcp comment 'SSH'

# Allow HTTP
sudo ufw allow 80/tcp comment 'HTTP'

# Allow HTTPS
sudo ufw allow 443/tcp comment 'HTTPS'

# Allow Backend API (optional, if direct access needed)
# Check if running non-interactively
if [ -t 0 ]; then
    read -p "Allow direct access to Backend API (port 8000)? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo ufw allow 8000/tcp comment 'Backend API'
    fi
else
    # Non-interactive mode - allow by default
    sudo ufw allow 8000/tcp comment 'Backend API'
fi

# Enable firewall
echo -e "${YELLOW}Enabling firewall...${NC}"
echo "y" | sudo ufw enable

echo -e "${GREEN}✓ Firewall configured${NC}"

# 6. Setup environment file
print_section "6. Setting Up Environment Variables"
ENV_FILE="$PROJECT_DIR/backend/.env"
ENV_EXAMPLE="$PROJECT_DIR/backend/.env.example"

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    
    # Generate JWT secret
    JWT_SECRET=$(openssl rand -hex 32)
    sed -i "s/your-very-secure-random-secret-key-minimum-32-characters/$JWT_SECRET/" "$ENV_FILE"
    
    echo -e "${GREEN}✓ Created .env file${NC}"
    echo -e "${YELLOW}⚠️  Please review and update $ENV_FILE if needed${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# 7. Create required directories
print_section "7. Creating Required Directories"
REQUIRED_DIRS=(
    "$PROJECT_DIR/storage"
    "$PROJECT_DIR/mongo-data"
    "$PROJECT_DIR/mongo-backup"
    "$PROJECT_DIR/backups"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "${GREEN}✓ Created $dir${NC}"
    else
        echo -e "${GREEN}✓ $dir already exists${NC}"
    fi
done

# Set permissions
chmod -R 755 "$PROJECT_DIR/storage" 2>/dev/null || true
chmod -R 755 "$PROJECT_DIR/mongo-data" 2>/dev/null || true

# 8. Setup Nginx (optional - for host-level reverse proxy)
print_section "8. Nginx Configuration"
NGINX_SETUP="n"
read -p "Do you want to configure Nginx on host as reverse proxy? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    NGINX_SETUP="y"
    echo -e "${YELLOW}Setting up Nginx reverse proxy...${NC}"
    
    # Get server IP
    SERVER_IP=$(hostname -I | awk '{print $1}')
    
    # Ask for domain name
    if [ -t 0 ]; then
        read -p "Enter domain name (or press Enter to use IP: $SERVER_IP): " DOMAIN_NAME
        if [ -z "$DOMAIN_NAME" ]; then
            DOMAIN_NAME="_"
        fi
    else
        # Non-interactive mode - use IP
        DOMAIN_NAME="_"
    fi
    
    # Create nginx config
    NGINX_CONFIG="/etc/nginx/sites-available/mnp"
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
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;
    
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
    
    # Frontend static files
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # SPA routing support
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
    
    # Enable site
    sudo ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/mnp
    
    # Remove default nginx site if exists
    if [ -f /etc/nginx/sites-enabled/default ]; then
        sudo rm /etc/nginx/sites-enabled/default
    fi
    
    # Test nginx config
    if sudo nginx -t; then
        echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
        sudo systemctl reload nginx
        echo -e "${GREEN}✓ Nginx reloaded${NC}"
        
        # Note: Need to update docker-compose.prod.yml to use port 8080 for frontend
        echo -e "${YELLOW}⚠️  Note: You need to update docker-compose.prod.yml to map frontend to port 8080${NC}"
        echo -e "${YELLOW}   Change frontend ports from '80:80' to '8080:80'${NC}"
    else
        echo -e "${RED}✗ Nginx configuration has errors${NC}"
    fi
else
    echo -e "${YELLOW}Skipping Nginx host configuration${NC}"
    echo -e "${CYAN}Note: Nginx in Docker container will handle reverse proxy${NC}"
fi

# 9. Summary
print_section "Setup Complete!"
echo -e "${GREEN}✓ All components installed and configured${NC}"
echo ""
echo -e "${CYAN}Next Steps:${NC}"
echo ""
echo -e "1. ${YELLOW}Review environment variables:${NC}"
echo -e "   ${BLUE}nano $ENV_FILE${NC}"
echo ""
echo -e "2. ${YELLOW}Build and start services:${NC}"
echo -e "   ${BLUE}cd $PROJECT_DIR${NC}"
echo -e "   ${BLUE}docker compose -f docker-compose.prod.yml up -d --build${NC}"
echo ""
echo -e "3. ${YELLOW}Check service status:${NC}"
echo -e "   ${BLUE}docker compose -f docker-compose.prod.yml ps${NC}"
echo ""
echo -e "4. ${YELLOW}View logs:${NC}"
echo -e "   ${BLUE}docker compose -f docker-compose.prod.yml logs -f${NC}"
echo ""
echo -e "5. ${YELLOW}Access the application:${NC}"
SERVER_IP=$(hostname -I | awk '{print $1}')
echo -e "   ${BLUE}Frontend: http://$SERVER_IP${NC}"
echo -e "   ${BLUE}Backend API: http://$SERVER_IP:8000/docs${NC}"
echo ""
echo -e "6. ${YELLOW}Default login credentials:${NC}"
echo -e "   ${BLUE}Username: admin${NC}"
echo -e "   ${BLUE}Password: admin123${NC}"
echo -e "   ${RED}⚠️  Change password immediately after first login!${NC}"
echo ""

if [[ "$NGINX_SETUP" == "y" ]] && [ -f "$NGINX_CONFIG" ]; then
    echo -e "${CYAN}Nginx Configuration:${NC}"
    echo -e "   ${BLUE}Config file: $NGINX_CONFIG${NC}"
    echo -e "   ${BLUE}To edit: sudo nano $NGINX_CONFIG${NC}"
    echo -e "   ${BLUE}To reload: sudo systemctl reload nginx${NC}"
    echo ""
fi

echo -e "${GREEN}Setup completed successfully!${NC}"
