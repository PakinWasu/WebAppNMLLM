#!/bin/bash

# สคริปต์สำหรับรัน setup ด้วย sudo
# ใช้เมื่อมีปัญหา Docker permission

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-dev}"

echo "=========================================="
echo "🔧 Running Setup with Sudo"
echo "=========================================="
echo ""
echo "⚠️  หมายเหตุ: สคริปต์นี้จะใช้ sudo สำหรับ Docker commands"
echo ""

# ตรวจสอบว่า user อยู่ใน docker group หรือไม่
if groups | grep -q docker; then
    echo "✅ User อยู่ใน docker group แล้ว"
    echo "   ไม่จำเป็นต้องใช้ sudo"
    echo ""
    ./setup-and-start.sh "$MODE"
else
    echo "⚠️  User ไม่อยู่ใน docker group"
    echo ""
    echo "📝 วิธีแก้ไข (เลือกวิธีใดวิธีหนึ่ง):"
    echo ""
    echo "1. เพิ่ม user เข้า docker group (แนะนำ):"
    echo "   sudo usermod -aG docker \$USER"
    echo "   newgrp docker"
    echo "   แล้วรัน: ./setup-and-start.sh"
    echo ""
    echo "2. ใช้ sudo กับคำสั่ง Docker โดยตรง:"
    echo ""
    
    # เลือก docker-compose file
    if [ "$MODE" = "prod" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
    else
        COMPOSE_FILE="docker-compose.yml"
    fi
    
    # ใช้ docker compose (v2) ถ้ามี
    if docker compose version &> /dev/null 2>&1; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    
    echo "   สร้างไฟล์ .env..."
    if [ ! -f "backend/.env" ]; then
        cp backend/.env.example backend/.env
        if command -v openssl &> /dev/null; then
            JWT_SECRET=$(openssl rand -hex 32)
        elif command -v python3 &> /dev/null; then
            JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        else
            JWT_SECRET="change-me-$(date +%s)"
        fi
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/JWT_SECRET=.*/JWT_SECRET=$JWT_SECRET/" backend/.env
        else
            sed -i "s/JWT_SECRET=.*/JWT_SECRET=$JWT_SECRET/" backend/.env
        fi
    fi
    
    echo "   สร้าง directories..."
    mkdir -p storage mongo-data mongo-backup
    sudo chmod -R 777 storage 2>/dev/null || true
    
    echo ""
    echo "   Build และ Start services..."
    echo "   คำสั่งที่จะรัน: sudo $DOCKER_COMPOSE -f $COMPOSE_FILE up -d --build"
    echo ""
    read -p "   กด Enter เพื่อดำเนินการต่อ หรือ Ctrl+C เพื่อยกเลิก..."
    
    sudo $DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d --build
    
    echo ""
    echo "⏳ รอให้ services พร้อม..."
    sleep 10
    
    echo ""
    echo "📊 สถานะ services:"
    sudo $DOCKER_COMPOSE -f "$COMPOSE_FILE" ps
    
    echo ""
    echo "✅ Setup เสร็จสิ้น!"
    echo ""
    echo "📋 URLs:"
    echo "  - Backend API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    if [ "$MODE" = "prod" ]; then
        echo "  - Frontend: http://localhost:8080"
    else
        echo "  - Frontend: http://localhost:5173"
    fi
    echo ""
    echo "🤖 Pull โมเดล LLM:"
    echo "   sudo docker exec mnp-ollama-prod ollama pull qwen2.5-coder:32b"
    echo "   หรือ: sudo ./pull-llm-model.sh"
    echo ""
fi
