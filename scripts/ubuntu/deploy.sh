#!/bin/bash
# Deploy Script for Ubuntu Server
# สคริปต์สำหรับ pull และ deploy บน Ubuntu Server

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Deploy Script for Ubuntu Server${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# ตรวจสอบว่าเป็น git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}Error: Not a git repository!${NC}"
    exit 1
fi

# ตรวจสอบว่า docker compose ทำงาน
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed!${NC}"
    exit 1
fi

# Backup (optional)
read -p "Do you want to backup before deploy? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Creating backup...${NC}"
    
    # Backup MongoDB
    if docker ps | grep -q mnp-mongo-prod; then
        BACKUP_DIR="./backups"
        mkdir -p $BACKUP_DIR
        DATE=$(date +%Y%m%d_%H%M%S)
        
        docker exec mnp-mongo-prod mongodump --archive=/backup/mongo-$DATE.archive 2>/dev/null || true
        docker cp mnp-mongo-prod:/backup/mongo-$DATE.archive $BACKUP_DIR/ 2>/dev/null || true
        
        echo -e "${GREEN}Backup created: $BACKUP_DIR/mongo-$DATE.archive${NC}"
    else
        echo -e "${YELLOW}MongoDB container not running, skipping backup${NC}"
    fi
fi

# Pull latest changes
echo ""
echo -e "${YELLOW}Pulling latest changes from GitHub...${NC}"
git fetch origin

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}Warning: You have uncommitted changes${NC}"
    read -p "Do you want to stash them? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git stash
        echo -e "${GREEN}✓ Changes stashed${NC}"
    fi
fi

git pull origin main

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to pull from GitHub!${NC}"
    echo -e "${YELLOW}Please resolve conflicts manually.${NC}"
    exit 1
fi

echo -e "${GREEN}Successfully pulled latest changes${NC}"

# ตรวจสอบว่ามีการเปลี่ยนแปลงหรือไม่
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo -e "${YELLOW}No new changes to deploy${NC}"
    read -p "Do you want to rebuild anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

# Rebuild และ restart
echo ""
echo -e "${YELLOW}Rebuilding and restarting services...${NC}"
docker compose -f docker-compose.prod.yml up -d --build

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to deploy!${NC}"
    exit 1
fi

# ตรวจสอบสถานะ
echo ""
echo -e "${YELLOW}Checking service status...${NC}"
sleep 5
docker compose -f docker-compose.prod.yml ps

# ตรวจสอบ health
echo ""
echo -e "${YELLOW}Checking service health...${NC}"
sleep 10

# ตรวจสอบ backend
if curl -f http://localhost:8000/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${RED}✗ Backend health check failed${NC}"
fi

# ตรวจสอบ frontend
if curl -f http://localhost > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is healthy${NC}"
else
    echo -e "${RED}✗ Frontend health check failed${NC}"
fi

# ดู logs
echo ""
read -p "Do you want to view logs? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker compose -f docker-compose.prod.yml logs --tail=50
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Services:${NC}"
echo -e "  Frontend: http://$(hostname -I | awk '{print $1}')"
echo -e "  Backend API: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
