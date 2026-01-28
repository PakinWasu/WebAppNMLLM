#!/bin/bash

# สคริปต์สำหรับตั้งค่าและเริ่มต้นระบบทั้งหมด
# Usage: ./setup-and-start.sh [dev|prod]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-dev}"

echo "=========================================="
echo "🚀 Network Project Platform Setup & Start"
echo "=========================================="
echo "Mode: $MODE"
echo ""

# ตรวจสอบ Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker ไม่พบ! กรุณาติดตั้ง Docker ก่อน"
    exit 1
fi

# ตรวจสอบ Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose ไม่พบ! กรุณาติดตั้ง Docker Compose ก่อน"
    exit 1
fi

# ใช้ docker compose (v2) ถ้ามี
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "✅ Docker และ Docker Compose พร้อมใช้งาน"
echo ""

# ตรวจสอบไฟล์ .env
if [ ! -f "backend/.env" ]; then
    echo "📝 สร้างไฟล์ backend/.env..."
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        
        # Generate JWT_SECRET
        if command -v openssl &> /dev/null; then
            JWT_SECRET=$(openssl rand -hex 32)
        elif command -v python3 &> /dev/null; then
            JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        else
            JWT_SECRET="change-me-$(date +%s)-$(shuf -i 1000-9999 -n 1)"
        fi
        
        # แทนที่ JWT_SECRET ในไฟล์ .env
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/JWT_SECRET=.*/JWT_SECRET=$JWT_SECRET/" backend/.env
        else
            # Linux
            sed -i "s/JWT_SECRET=.*/JWT_SECRET=$JWT_SECRET/" backend/.env
        fi
        
        echo "✅ สร้างไฟล์ .env พร้อม JWT_SECRET ที่ปลอดภัย"
    else
        echo "❌ ไม่พบไฟล์ backend/.env.example"
        exit 1
    fi
else
    echo "✅ ไฟล์ backend/.env มีอยู่แล้ว"
fi

# สร้าง directories ที่จำเป็น
echo ""
echo "📁 สร้าง directories ที่จำเป็น..."
mkdir -p storage
mkdir -p mongo-data
mkdir -p mongo-backup
chmod -R 777 storage 2>/dev/null || true
echo "✅ สร้าง directories เสร็จสิ้น"

# เลือก docker-compose file
if [ "$MODE" = "prod" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    echo ""
    echo "🏭 ใช้ Production mode"
else
    COMPOSE_FILE="docker-compose.yml"
    echo ""
    echo "💻 ใช้ Development mode"
fi

# Stop containers เก่า (ถ้ามี)
echo ""
echo "🛑 หยุด containers เก่า (ถ้ามี)..."
$DOCKER_COMPOSE -f "$COMPOSE_FILE" down 2>/dev/null || true

# Build และ Start services
echo ""
echo "🔨 Build และ Start services..."
$DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d --build

# รอให้ services พร้อม
echo ""
echo "⏳ รอให้ services พร้อมใช้งาน..."
sleep 10

# ตรวจสอบสถานะ
echo ""
echo "📊 ตรวจสอบสถานะ services..."
$DOCKER_COMPOSE -f "$COMPOSE_FILE" ps

# รอให้ MongoDB พร้อม
echo ""
echo "⏳ รอให้ MongoDB พร้อม..."
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if $DOCKER_COMPOSE -f "$COMPOSE_FILE" exec -T mongodb mongo --eval "db.runCommand('ping').ok" &>/dev/null; then
        echo "✅ MongoDB พร้อมใช้งาน"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "  รอ MongoDB... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "⚠️  MongoDB ยังไม่พร้อม แต่จะดำเนินการต่อ..."
fi

# รอให้ Backend พร้อม
echo ""
echo "⏳ รอให้ Backend พร้อม..."
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/docs &>/dev/null; then
        echo "✅ Backend พร้อมใช้งาน"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "  รอ Backend... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "⚠️  Backend ยังไม่พร้อม แต่จะดำเนินการต่อ..."
fi

# ตรวจสอบ Ollama และ pull โมเดล
echo ""
echo "🤖 ตรวจสอบ Ollama..."
OLLAMA_CONTAINER="mnp-ollama"
if [ "$MODE" = "prod" ]; then
    OLLAMA_CONTAINER="mnp-ollama-prod"
fi

if docker ps | grep -q "$OLLAMA_CONTAINER"; then
    echo "✅ Ollama container ทำงานอยู่"
    
    # รอให้ Ollama พร้อม
    echo "⏳ รอให้ Ollama พร้อม..."
    sleep 5
    
    # ตรวจสอบว่าโมเดลถูก pull แล้วหรือยัง
    MODEL_NAME=$(grep AI_MODEL_NAME backend/.env | cut -d '=' -f2)
    echo "📥 ตรวจสอบโมเดล: $MODEL_NAME"
    
    if docker exec "$OLLAMA_CONTAINER" ollama list 2>/dev/null | grep -q "$MODEL_NAME"; then
        echo "✅ โมเดล $MODEL_NAME มีอยู่แล้ว"
    else
        echo "📥 กำลังดาวน์โหลดโมเดล $MODEL_NAME..."
        echo "   ⚠️  โมเดลขนาดใหญ่ (~18GB) อาจใช้เวลานานในการดาวน์โหลด"
        echo "   ⚠️  ต้องการ RAM ~16-20GB และ Disk space ~18GB"
        echo ""
        docker exec "$OLLAMA_CONTAINER" ollama pull "$MODEL_NAME" || {
            echo "⚠️  ไม่สามารถ pull โมเดลได้ แต่จะดำเนินการต่อ..."
            echo "   คุณสามารถ pull โมเดลด้วยตนเองด้วยคำสั่ง:"
            echo "   docker exec $OLLAMA_CONTAINER ollama pull $MODEL_NAME"
            echo ""
            echo "   หรือใช้สคริปต์: ./pull-llm-model.sh"
        }
    fi
else
    echo "⚠️  Ollama container ไม่พบ"
fi

# สร้าง admin user (ถ้ายังไม่มี)
echo ""
echo "👤 ตรวจสอบ admin user..."
if docker ps | grep -q "mnp-backend"; then
    BACKEND_CONTAINER="mnp-backend"
elif docker ps | grep -q "mnp-backend-prod"; then
    BACKEND_CONTAINER="mnp-backend-prod"
else
    BACKEND_CONTAINER=""
fi

if [ -n "$BACKEND_CONTAINER" ]; then
    echo "  รันสคริปต์ seed admin..."
    docker exec "$BACKEND_CONTAINER" python /app/scripts/seed_admin.py 2>/dev/null || {
        echo "  ⚠️  ไม่สามารถสร้าง admin user ได้ (อาจมีอยู่แล้ว)"
    }
fi

# แสดงสรุป
echo ""
echo "=========================================="
echo "✅ Setup เสร็จสิ้น!"
echo "=========================================="
echo ""
echo "📋 สรุป:"
echo "  - Backend API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
if [ "$MODE" = "prod" ]; then
    echo "  - Frontend: http://localhost:8080"
else
    echo "  - Frontend: http://localhost:5173"
fi
echo "  - Ollama: http://localhost:11434"
echo ""
echo "👤 ข้อมูล Login เริ่มต้น:"
echo "  - Username: admin"
echo "  - Password: admin123"
echo ""
echo "⚠️  เปลี่ยนรหัสผ่านทันทีหลังจาก login ครั้งแรก!"
echo ""
echo "📝 คำสั่งที่มีประโยชน์:"
echo "  - ดู logs: $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f"
echo "  - หยุด services: $DOCKER_COMPOSE -f $COMPOSE_FILE down"
echo "  - Restart: $DOCKER_COMPOSE -f $COMPOSE_FILE restart"
echo ""
echo "📚 เอกสารเพิ่มเติม:"
echo "  - LLM_SETUP.md - คู่มือการตั้งค่า LLM"
echo "  - README.md - คู่มือหลัก"
echo ""
