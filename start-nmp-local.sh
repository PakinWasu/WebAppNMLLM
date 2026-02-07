#!/bin/bash
# เริ่มโปรเจคและตั้งค่า Nginx + DNS สำหรับ nmp.local
# ใช้งาน: ./start-nmp-local.sh
# หลังรันเสร็จ ให้รัน (ด้วย sudo): sudo ./setup-nmp-local-nginx.sh แล้ว sudo ./setup-hosts-linux.sh 127.0.0.1

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  WebAppNMLLM - เริ่มด้วย nmp.local${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# เตรียม .env และโฟลเดอร์ (เหมือน run-on-ubuntu-server.sh)
if [ ! -f backend/.env ]; then
    echo -e "${YELLOW}สร้าง backend/.env...${NC}"
    cp backend/.env.example backend/.env
    JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || echo "change-me-$(date +%s)")
    sed -i "s/your-very-secure-random-secret-key-minimum-32-characters/$JWT_SECRET/" backend/.env
    sed -i 's|OLLAMA_BASE_URL=.*|OLLAMA_BASE_URL=http://ollama:11434|' backend/.env
    echo -e "${GREEN}✓ สร้าง backend/.env แล้ว${NC}"
fi
mkdir -p storage mongo-data mongo-backup backups
chmod -R 755 storage mongo-data 2>/dev/null || true

# ติดตั้ง Docker ถ้ายังไม่มี
if ! command -v docker &>/dev/null; then
    echo -e "${YELLOW}ยังไม่มี Docker – กำลังติดตั้ง (จะถามรหัส sudo)...${NC}"
    chmod +x scripts/ubuntu/setup-ubuntu-server.sh 2>/dev/null || true
    NON_INTERACTIVE=1 ./scripts/ubuntu/setup-ubuntu-server.sh
    echo ""
    echo -e "${YELLOW}กำลัง build และ start แอป...${NC}"
    sg docker -c "cd '$SCRIPT_DIR' && docker compose -f docker-compose.prod.yml up -d --build"
else
    echo -e "${YELLOW}กำลัง build และ start แอป...${NC}"
    docker compose -f docker-compose.prod.yml up -d --build
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  แอปทำงานแล้ว${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  ${CYAN}เข้าผ่านพอร์ตโดยตรง:${NC}"
echo -e "    Frontend:  http://localhost:8080"
echo -e "    Backend:   http://localhost:8000/docs"
echo ""
echo -e "  ${YELLOW}เพื่อใช้ชื่อ nmp.local (port 80):${NC}"
echo -e "    1) ตั้งค่า Nginx บน host:"
echo -e "       ${CYAN}sudo ./setup-nmp-local-nginx.sh${NC}"
echo -e "    2) ตั้งค่า DNS (hosts) ให้ nmp.local ชี้มาที่เครื่องนี้:"
echo -e "       ${CYAN}sudo ./setup-hosts-linux.sh 127.0.0.1${NC}"
echo -e "       (หรือใช้ IP เครื่องอื่นถ้าเข้าจาก LAN: sudo ./setup-hosts-linux.sh <IP>)"
echo ""
echo -e "  หลังตั้งค่าแล้ว เปิดเบราว์เซอร์: ${GREEN}http://nmp.local${NC}"
echo -e "  ${CYAN}Login:${NC} admin / admin123"
echo ""
