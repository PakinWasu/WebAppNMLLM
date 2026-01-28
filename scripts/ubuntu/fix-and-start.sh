#!/bin/bash
# Fix and Start Script - แก้ไขปัญหาและเริ่มใช้งานให้อัตโนมัติ

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
echo -e "${CYAN}Fix and Start Application${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

cd "$PROJECT_DIR"

# Step 1: Stop nginx on host
echo -e "${YELLOW}Step 1: Stopping nginx on host...${NC}"
if systemctl is-active --quiet nginx 2>/dev/null; then
    if sudo systemctl stop nginx 2>/dev/null; then
        echo -e "${GREEN}✓ Nginx stopped${NC}"
        sudo systemctl disable nginx 2>/dev/null || true
    else
        echo -e "${RED}✗ Cannot stop nginx. Please run: sudo systemctl stop nginx${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Nginx is already stopped${NC}"
fi

# Step 2: Stop existing containers
echo ""
echo -e "${YELLOW}Step 2: Stopping existing containers...${NC}"
docker compose -f docker-compose.prod.yml down 2>/dev/null || true
sleep 2

# Step 3: Start all services
echo ""
echo -e "${YELLOW}Step 3: Starting all services...${NC}"
docker compose -f docker-compose.prod.yml up -d

# Step 4: Wait for services
echo ""
echo -e "${YELLOW}Step 4: Waiting for services to be ready...${NC}"
sleep 10

# Step 5: Check status
echo ""
echo -e "${CYAN}Step 5: Checking service status...${NC}"
docker compose -f docker-compose.prod.yml ps

# Step 6: Test access
echo ""
echo -e "${CYAN}Step 6: Testing access...${NC}"
SERVER_IP=$(hostname -I | awk '{print $1}')

BACKEND_OK=false
FRONTEND_OK=false

# Test backend
if curl -s http://localhost:8000/docs >/dev/null 2>&1; then
    BACKEND_OK=true
    echo -e "${GREEN}✓ Backend is accessible${NC}"
else
    echo -e "${YELLOW}⚠ Backend is starting...${NC}"
fi

# Test frontend
sleep 5
if curl -s http://localhost 2>&1 | grep -q "<!DOCTYPE html\|<html"; then
    FRONTEND_OK=true
    echo -e "${GREEN}✓ Frontend is accessible${NC}"
elif curl -s http://localhost 2>&1 | grep -q "502"; then
    echo -e "${YELLOW}⚠ Frontend may still be starting (502 error)${NC}"
    echo -e "${YELLOW}   Waiting a bit more...${NC}"
    sleep 10
    if curl -s http://localhost 2>&1 | grep -q "<!DOCTYPE html\|<html"; then
        FRONTEND_OK=true
        echo -e "${GREEN}✓ Frontend is now accessible${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Frontend is starting...${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Access URLs:${NC}"
echo -e "   ${BLUE}Frontend: http://$SERVER_IP${NC}"
echo -e "   ${BLUE}Backend API: http://$SERVER_IP:8000/docs${NC}"
echo ""
echo -e "${CYAN}Default Login:${NC}"
echo -e "   ${BLUE}Username: admin${NC}"
echo -e "   ${BLUE}Password: admin123${NC}"
echo -e "   ${RED}⚠️  Change password immediately!${NC}"
echo ""

if [ "$FRONTEND_OK" = true ] && [ "$BACKEND_OK" = true ]; then
    echo -e "${GREEN}✓ All services are ready!${NC}"
elif [ "$BACKEND_OK" = true ]; then
    echo -e "${YELLOW}⚠ Backend is ready, frontend may need a moment${NC}"
    echo -e "${YELLOW}   Try accessing in a few seconds${NC}"
else
    echo -e "${YELLOW}⚠ Services are still starting${NC}"
    echo -e "${YELLOW}   Check logs: docker compose -f docker-compose.prod.yml logs${NC}"
fi

echo ""
echo -e "${CYAN}Useful commands:${NC}"
echo -e "   ${BLUE}View logs: docker compose -f docker-compose.prod.yml logs -f${NC}"
echo -e "   ${BLUE}Restart: docker compose -f docker-compose.prod.yml restart${NC}"
echo -e "   ${BLUE}Stop: docker compose -f docker-compose.prod.yml down${NC}"
