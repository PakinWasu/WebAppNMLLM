#!/bin/bash
# Fix 502 Bad Gateway Error
# แก้ไขปัญหา 502 Bad Gateway ที่เกิดจาก nginx บน host

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Fix 502 Bad Gateway Error${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Check if nginx on host is running
if systemctl is-active --quiet nginx 2>/dev/null; then
    echo -e "${YELLOW}Nginx on host is running and blocking port 80${NC}"
    echo -e "${YELLOW}This prevents Docker frontend container from binding to port 80${NC}"
    echo ""
    echo -e "${CYAN}Solution: Stop nginx on host${NC}"
    echo ""
    echo -e "${YELLOW}Run these commands:${NC}"
    echo -e "  ${BLUE}sudo systemctl stop nginx${NC}"
    echo -e "  ${BLUE}sudo systemctl disable nginx${NC}"
    echo ""
    echo -e "${YELLOW}Then restart frontend container:${NC}"
    echo -e "  ${BLUE}cd $(pwd)${NC}"
    echo -e "  ${BLUE}docker compose -f docker-compose.prod.yml restart frontend${NC}"
    echo ""
    
    # Try to stop nginx (will fail if no sudo, but show the command)
    echo -e "${YELLOW}Attempting to stop nginx...${NC}"
    if sudo systemctl stop nginx 2>/dev/null; then
        echo -e "${GREEN}✓ Nginx stopped${NC}"
        sudo systemctl disable nginx 2>/dev/null || true
        
        # Restart frontend
        echo ""
        echo -e "${YELLOW}Restarting frontend container...${NC}"
        cd "$(dirname "$0")/../.."
        docker compose -f docker-compose.prod.yml restart frontend
        
        sleep 3
        
        # Check if frontend is accessible
        echo ""
        echo -e "${YELLOW}Checking frontend...${NC}"
        if curl -s http://localhost >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Frontend is now accessible!${NC}"
        else
            echo -e "${YELLOW}Frontend may still be starting up...${NC}"
        fi
    else
        echo -e "${RED}✗ Cannot stop nginx (need sudo privileges)${NC}"
        echo ""
        echo -e "${YELLOW}Please run manually:${NC}"
        echo -e "  ${BLUE}sudo systemctl stop nginx${NC}"
        echo -e "  ${BLUE}sudo systemctl disable nginx${NC}"
        echo -e "  ${BLUE}cd $(pwd) && docker compose -f docker-compose.prod.yml restart frontend${NC}"
    fi
else
    echo -e "${GREEN}✓ Nginx on host is not running${NC}"
    
    # Check if frontend container has port mapping
    cd "$(dirname "$0")/../.."
    FRONTEND_PORTS=$(docker compose -f docker-compose.prod.yml ps frontend 2>/dev/null | grep -o "0.0.0.0:[0-9]*->80" || echo "")
    
    if [ -z "$FRONTEND_PORTS" ]; then
        echo -e "${YELLOW}Frontend container doesn't have port mapping${NC}"
        echo -e "${YELLOW}Restarting frontend container...${NC}"
        docker compose -f docker-compose.prod.yml restart frontend
        
        sleep 3
        
        # Check again
        FRONTEND_PORTS=$(docker compose -f docker-compose.prod.yml ps frontend 2>/dev/null | grep -o "0.0.0.0:[0-9]*->80" || echo "")
        if [ -n "$FRONTEND_PORTS" ]; then
            echo -e "${GREEN}✓ Frontend port mapping restored: $FRONTEND_PORTS${NC}"
        else
            echo -e "${YELLOW}Still no port mapping. Checking logs...${NC}"
            docker compose -f docker-compose.prod.yml logs frontend --tail=10
        fi
    else
        echo -e "${GREEN}✓ Frontend has port mapping: $FRONTEND_PORTS${NC}"
    fi
fi

echo ""
echo -e "${CYAN}Testing access...${NC}"
SERVER_IP=$(hostname -I | awk '{print $1}')

if curl -s http://localhost >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is accessible at http://$SERVER_IP${NC}"
elif curl -s http://localhost:8000/docs >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is accessible at http://$SERVER_IP:8000/docs${NC}"
    echo -e "${YELLOW}Frontend may need a moment to start${NC}"
else
    echo -e "${YELLOW}Services may still be starting...${NC}"
fi

echo ""
echo -e "${CYAN}Current status:${NC}"
docker compose -f docker-compose.prod.yml ps 2>/dev/null | grep -E "NAME|frontend|backend" || echo "Cannot get status"
