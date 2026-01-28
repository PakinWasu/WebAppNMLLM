#!/bin/bash

# สคริปต์ตรวจสอบและแก้ไขปัญหาอัตโนมัติ
# Usage: ./check-and-fix.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "🔍 ตรวจสอบและแก้ไขปัญหาโปรเจค"
echo "=========================================="
echo ""

# ตรวจสอบ Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker ไม่พบ! กรุณาติดตั้ง Docker ก่อน"
    exit 1
fi

# ตรวจสอบ Docker Compose
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ Docker Compose ไม่พบ!"
    exit 1
fi

echo "✅ Docker และ Docker Compose พร้อมใช้งาน"
echo ""

# ตรวจสอบไฟล์ .env
if [ ! -f "backend/.env" ]; then
    echo "❌ ไม่พบไฟล์ backend/.env"
    echo "📝 สร้างไฟล์ .env..."
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        echo "✅ สร้างไฟล์ .env จาก .env.example"
    else
        echo "❌ ไม่พบไฟล์ backend/.env.example"
        exit 1
    fi
else
    echo "✅ ไฟล์ backend/.env มีอยู่แล้ว"
fi

# ตรวจสอบ directories
echo ""
echo "📁 ตรวจสอบ directories..."
mkdir -p storage mongo-data mongo-backup
chmod -R 777 storage 2>/dev/null || true
echo "✅ Directories พร้อมใช้งาน"

# ตรวจสอบว่า containers ทำงานอยู่หรือไม่
echo ""
echo "🐳 ตรวจสอบ Docker containers..."

# หา compose file ที่ใช้งาน
if [ -f "docker-compose.prod.yml" ] && docker ps | grep -q "mnp-backend-prod"; then
    COMPOSE_FILE="docker-compose.prod.yml"
    MODE="prod"
elif docker ps | grep -q "mnp-backend"; then
    COMPOSE_FILE="docker-compose.yml"
    MODE="dev"
else
    echo "⚠️  ไม่พบ containers ที่ทำงานอยู่"
    echo "   รัน: ./setup-and-start.sh เพื่อ start services"
    exit 0
fi

echo "✅ พบ containers ที่ทำงานอยู่ (Mode: $MODE)"
echo ""

# ตรวจสอบ MongoDB
echo "📊 ตรวจสอบ MongoDB..."
if docker ps | grep -q "mnp-mongo"; then
    MONGO_CONTAINER="mnp-mongo"
elif docker ps | grep -q "mnp-mongo-prod"; then
    MONGO_CONTAINER="mnp-mongo-prod"
else
    echo "⚠️  MongoDB container ไม่พบ"
    MONGO_CONTAINER=""
fi

if [ -n "$MONGO_CONTAINER" ]; then
    if docker exec "$MONGO_CONTAINER" mongo --eval "db.runCommand('ping').ok" &>/dev/null; then
        echo "✅ MongoDB ทำงานปกติ"
    else
        echo "⚠️  MongoDB ไม่ตอบสนอง"
    fi
fi

# ตรวจสอบ Backend
echo ""
echo "🔧 ตรวจสอบ Backend..."
if docker ps | grep -q "mnp-backend"; then
    BACKEND_CONTAINER="mnp-backend"
elif docker ps | grep -q "mnp-backend-prod"; then
    BACKEND_CONTAINER="mnp-backend-prod"
else
    echo "⚠️  Backend container ไม่พบ"
    BACKEND_CONTAINER=""
fi

if [ -n "$BACKEND_CONTAINER" ]; then
    if curl -s http://localhost:8000/docs &>/dev/null; then
        echo "✅ Backend API ทำงานปกติ (http://localhost:8000)"
    else
        echo "⚠️  Backend API ไม่ตอบสนอง"
        echo "   ตรวจสอบ logs: docker logs $BACKEND_CONTAINER"
    fi
fi

# ตรวจสอบ Ollama
echo ""
echo "🤖 ตรวจสอบ Ollama..."
if docker ps | grep -q "mnp-ollama-prod"; then
    OLLAMA_CONTAINER="mnp-ollama-prod"
elif docker ps | grep -q "mnp-ollama"; then
    OLLAMA_CONTAINER="mnp-ollama"
else
    echo "⚠️  Ollama container ไม่พบ"
    echo "   Start services: ./setup-and-start.sh"
    OLLAMA_CONTAINER=""
fi

if [ -n "$OLLAMA_CONTAINER" ]; then
    echo "✅ Ollama container ทำงานอยู่"
    
    # ตรวจสอบว่า Ollama API ตอบสนอง
    if curl -s http://localhost:11434/api/tags &>/dev/null; then
        echo "✅ Ollama API ทำงานปกติ"
    else
        echo "⚠️  Ollama API ไม่ตอบสนอง"
        echo "   ตรวจสอบ logs: docker logs $OLLAMA_CONTAINER"
    fi
    
    # ตรวจสอบโมเดล
    echo ""
    echo "📥 ตรวจสอบโมเดล LLM..."
    if [ -f "backend/.env" ]; then
        MODEL_NAME=$(grep AI_MODEL_NAME backend/.env | cut -d '=' -f2 | tr -d ' ')
        echo "   โมเดลที่กำหนด: $MODEL_NAME"
        
        if docker exec "$OLLAMA_CONTAINER" ollama list 2>/dev/null | grep -q "$MODEL_NAME"; then
            echo "✅ โมเดล $MODEL_NAME พร้อมใช้งาน"
        else
            echo "⚠️  โมเดล $MODEL_NAME ยังไม่ถูกดาวน์โหลด"
            echo ""
            read -p "   ดาวน์โหลดโมเดลตอนนี้? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "📥 กำลังดาวน์โหลดโมเดล $MODEL_NAME..."
                docker exec "$OLLAMA_CONTAINER" ollama pull "$MODEL_NAME" || {
                    echo "❌ ไม่สามารถดาวน์โหลดโมเดลได้"
                    echo "   รันด้วยตนเอง: docker exec $OLLAMA_CONTAINER ollama pull $MODEL_NAME"
                }
            else
                echo "   ข้ามการดาวน์โหลดโมเดล"
                echo "   รันภายหลัง: ./pull-llm-model.sh"
            fi
        fi
    fi
    
    # ทดสอบการเชื่อมต่อจาก Backend
    if [ -n "$BACKEND_CONTAINER" ]; then
        echo ""
        echo "🔗 ทดสอบการเชื่อมต่อ Backend → Ollama..."
        if docker exec "$BACKEND_CONTAINER" curl -s http://ollama:11434/api/tags &>/dev/null; then
            echo "✅ Backend สามารถเชื่อมต่อกับ Ollama ได้"
        else
            echo "⚠️  Backend ไม่สามารถเชื่อมต่อกับ Ollama ได้"
            echo "   ตรวจสอบ network: docker network inspect mnp-network"
        fi
    fi
fi

# สรุป
echo ""
echo "=========================================="
echo "✅ การตรวจสอบเสร็จสิ้น"
echo "=========================================="
echo ""
echo "📋 สรุป:"
echo "  - Backend: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
if [ "$MODE" = "prod" ]; then
    echo "  - Frontend: http://localhost:8080"
else
    echo "  - Frontend: http://localhost:5173"
fi
echo "  - Ollama: http://localhost:11434"
echo ""
echo "📝 คำสั่งที่มีประโยชน์:"
echo "  - ดู logs: $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f"
echo "  - Restart: $DOCKER_COMPOSE -f $COMPOSE_FILE restart"
echo "  - Pull โมเดล: ./pull-llm-model.sh"
echo ""
