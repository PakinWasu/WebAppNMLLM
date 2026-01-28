#!/bin/bash
# Fix Port Conflict Script
# แก้ไขปัญหา port conflict ระหว่าง nginx บน host กับ Docker container

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Port Conflict Fix Script${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Check if nginx on host is running
if systemctl is-active --quiet nginx 2>/dev/null; then
    echo -e "${YELLOW}Nginx on host is running and using port 80${NC}"
    echo -e "${YELLOW}Options:${NC}"
    echo -e "  1. Stop nginx on host (recommended if using Docker nginx)"
    echo -e "  2. Change Docker frontend port to 8080"
    echo ""
    read -p "Choose option (1 or 2): " OPTION
    
    if [ "$OPTION" = "1" ]; then
        echo -e "${YELLOW}Stopping nginx on host...${NC}"
        sudo systemctl stop nginx
        sudo systemctl disable nginx 2>/dev/null || true
        echo -e "${GREEN}✓ Nginx stopped${NC}"
    elif [ "$OPTION" = "2" ]; then
        echo -e "${YELLOW}You need to use docker-compose.prod-nginx-host.yml instead${NC}"
        echo -e "${YELLOW}And configure nginx on host to proxy to port 8080${NC}"
        exit 0
    fi
else
    echo -e "${GREEN}✓ Nginx on host is not running${NC}"
fi

# Check if port 80 is still in use
if sudo lsof -i :80 >/dev/null 2>&1 || sudo netstat -tuln | grep -q ":80 "; then
    echo -e "${YELLOW}Port 80 is still in use. Checking what's using it...${NC}"
    sudo lsof -i :80 2>/dev/null || sudo netstat -tulpn | grep ":80 "
    echo ""
    echo -e "${RED}Please stop the service using port 80 manually${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Port 80 is available${NC}"
fi

echo ""
echo -e "${GREEN}Port conflict resolved!${NC}"
echo -e "${CYAN}You can now start Docker containers:${NC}"
echo -e "  ${YELLOW}docker compose -f docker-compose.prod.yml up -d${NC}"
