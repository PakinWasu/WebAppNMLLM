#!/bin/bash
# Auto Setup Script for Ubuntu Server
# สคริปต์สำหรับติดตั้งและรันโปรเจคอัตโนมัติทั้งหมด

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
echo -e "${CYAN}Auto Setup and Deploy Script${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Error: Please do not run as root. Run as regular user with sudo privileges.${NC}"
   exit 1
fi

# 1. Run setup script (non-interactive mode)
echo -e "${YELLOW}Step 1: Running setup script...${NC}"
echo ""

# Check if we need to run setup
NEED_SETUP=false

if ! command -v docker >/dev/null 2>&1; then
    NEED_SETUP=true
elif ! docker compose version >/dev/null 2>&1; then
    NEED_SETUP=true
elif [ ! -f "$PROJECT_DIR/backend/.env" ]; then
    NEED_SETUP=true
fi

if [ "$NEED_SETUP" = true ]; then
    echo -e "${YELLOW}Running initial setup...${NC}"
    # Run setup non-interactively (pipe empty input)
    </dev/null bash "$SCRIPT_DIR/setup-ubuntu-server.sh" || {
        echo -e "${RED}Setup failed. Please run manually: $SCRIPT_DIR/setup-ubuntu-server.sh${NC}"
        exit 1
    }
    
    # Wait a bit for docker group to be active
    echo ""
    echo -e "${YELLOW}Waiting for docker group to be active...${NC}"
    sleep 3
    
    # Check if docker is accessible, if not try sg
    if ! docker ps >/dev/null 2>&1; then
        echo -e "${YELLOW}Docker group not active. Trying sg to activate...${NC}"
        if command -v sg >/dev/null 2>&1; then
            exec sg docker -c "bash $0"
        else
            echo -e "${YELLOW}Please logout and login again, or run: newgrp docker${NC}"
            echo -e "${YELLOW}Then run this script again.${NC}"
            exit 1
        fi
    fi
else
    echo -e "${GREEN}✓ Setup already completed${NC}"
    
    # Still check docker access
    if ! docker ps >/dev/null 2>&1; then
        echo -e "${YELLOW}Docker not accessible. Trying sg...${NC}"
        if command -v sg >/dev/null 2>&1; then
            exec sg docker -c "bash $0"
        fi
    fi
fi

# 2. Change to project directory
cd "$PROJECT_DIR"

# 3. Check if .env exists
if [ ! -f "backend/.env" ]; then
    echo -e "${RED}Error: .env file not found. Please run setup script first.${NC}"
    exit 1
fi

# 4. Stop any existing containers
echo ""
echo -e "${YELLOW}Step 2: Stopping any existing containers...${NC}"
docker compose -f docker-compose.prod.yml down 2>/dev/null || true
docker compose -f docker-compose.prod-nginx-host.yml down 2>/dev/null || true

# 5. Build and start services
echo ""
echo -e "${YELLOW}Step 3: Building and starting services...${NC}"
echo -e "${CYAN}This may take several minutes...${NC}"
echo ""

# Use default docker-compose.prod.yml (Nginx in Docker)
docker compose -f docker-compose.prod.yml up -d --build

# 6. Wait for services to be healthy
echo ""
echo -e "${YELLOW}Step 4: Waiting for services to be ready...${NC}"
sleep 10

# Check service status
MAX_RETRIES=30
RETRY_COUNT=0
BACKEND_READY=false
FRONTEND_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Check backend
    if curl -f http://localhost:8000/docs >/dev/null 2>&1; then
        if [ "$BACKEND_READY" = false ]; then
            echo -e "${GREEN}✓ Backend is ready${NC}"
            BACKEND_READY=true
        fi
    fi
    
    # Check frontend
    if curl -f http://localhost >/dev/null 2>&1; then
        if [ "$FRONTEND_READY" = false ]; then
            echo -e "${GREEN}✓ Frontend is ready${NC}"
            FRONTEND_READY=true
        fi
    fi
    
    if [ "$BACKEND_READY" = true ] && [ "$FRONTEND_READY" = true ]; then
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}Waiting... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 5
done

# 7. Show status
echo ""
echo -e "${CYAN}Step 5: Service Status${NC}"
docker compose -f docker-compose.prod.yml ps

# 8. Show summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup and Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

SERVER_IP=$(hostname -I | awk '{print $1}')

echo -e "${CYAN}Access URLs:${NC}"
echo -e "   ${BLUE}Frontend: http://$SERVER_IP${NC}"
echo -e "   ${BLUE}Backend API: http://$SERVER_IP:8000/docs${NC}"
echo ""

echo -e "${CYAN}Default Login:${NC}"
echo -e "   ${BLUE}Username: admin${NC}"
echo -e "   ${BLUE}Password: admin123${NC}"
echo -e "   ${RED}⚠️  Change password immediately after first login!${NC}"
echo ""

echo -e "${CYAN}Useful Commands:${NC}"
echo -e "   ${BLUE}View logs: docker compose -f docker-compose.prod.yml logs -f${NC}"
echo -e "   ${BLUE}Restart: docker compose -f docker-compose.prod.yml restart${NC}"
echo -e "   ${BLUE}Stop: docker compose -f docker-compose.prod.yml down${NC}"
echo ""

if [ "$BACKEND_READY" = false ] || [ "$FRONTEND_READY" = false ]; then
    echo -e "${YELLOW}⚠️  Some services may still be starting up${NC}"
    echo -e "${YELLOW}   Check logs: docker compose -f docker-compose.prod.yml logs${NC}"
fi
