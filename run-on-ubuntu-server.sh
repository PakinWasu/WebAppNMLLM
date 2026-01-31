#!/bin/bash
# รันโปรเจคบน Ubuntu Server (Setup + Build + Start)
# รันคำสั่งเดียว – ถ้ายังไม่มี Docker จะติดตั้งให้ แล้ว start แอปให้ใช้ได้เลย (ไม่ต้อง logout)
#
# การใช้งาน:
#   chmod +x run-on-ubuntu-server.sh
#   ./run-on-ubuntu-server.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  WebAppNMLLM - ใช้ได้เลย${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# เตรียม .env และโฟลเดอร์ก่อน (ทำได้โดยไม่ต้องมี Docker)
if [ ! -f backend/.env ]; then
    echo -e "${YELLOW}สร้าง backend/.env...${NC}"
    cp backend/.env.example backend/.env
    JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || echo "change-me-$(date +%s)")
    sed -i "s/your-very-secure-random-secret-key-minimum-32-characters/$JWT_SECRET/" backend/.env
    echo -e "${GREEN}✓ สร้าง backend/.env แล้ว${NC}"
fi
mkdir -p storage mongo-data mongo-backup backups
chmod -R 755 storage mongo-data 2>/dev/null || true

# 1. ถ้ายังไม่มี Docker ให้รัน setup (จะถามรหัส sudo)
if ! command -v docker &>/dev/null; then
    echo -e "${YELLOW}ยังไม่มี Docker – กำลังติดตั้ง (จะถามรหัส sudo)...${NC}"
    chmod +x scripts/ubuntu/setup-ubuntu-server.sh
    NON_INTERACTIVE=1 ./scripts/ubuntu/setup-ubuntu-server.sh
    # ใช้ sg docker เพื่อรัน docker ใน session เดิมโดยไม่ต้อง logout
    echo ""
    echo -e "${YELLOW}กำลัง build และ start แอป...${NC}"
    sg docker -c "cd '$SCRIPT_DIR' && docker compose -f docker-compose.prod.yml up -d --build"
else
    # 2. มี Docker อยู่แล้ว – build และ start
    echo -e "${YELLOW}กำลัง build และ start แอป...${NC}"
    docker compose -f docker-compose.prod.yml up -d --build
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ใช้งานได้แล้ว${NC}"
echo -e "${GREEN}========================================${NC}"
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
echo ""
echo -e "  ${CYAN}Frontend:${NC}  http://${SERVER_IP}:8080"
echo -e "  ${CYAN}Backend API:${NC} http://${SERVER_IP}:8000/docs"
echo ""
echo -e "  ${CYAN}Login:${NC} admin / admin123"
echo -e "  ${YELLOW}⚠️  เปลี่ยนรหัสผ่านหลังล็อกอินครั้งแรก${NC}"
echo ""
echo -e "  ดู logs:  ${CYAN}docker compose -f docker-compose.prod.yml logs -f${NC}"
echo -e "  หยุดแอป: ${CYAN}docker compose -f docker-compose.prod.yml down${NC}"
echo ""
