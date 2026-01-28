#!/bin/bash

# สคริปต์ Quick Start สำหรับเริ่มต้นระบบอย่างรวดเร็ว
# Usage: ./quick-start.sh [dev|prod]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-dev}"

echo "=========================================="
echo "⚡ Quick Start - Network Project Platform"
echo "=========================================="
echo ""

# ตรวจสอบว่า setup เรียบร้อยแล้วหรือยัง
if [ ! -f "backend/.env" ]; then
    echo "📝 ยังไม่ได้ setup กำลังรัน setup..."
    ./setup-and-start.sh "$MODE"
else
    echo "✅ ไฟล์ .env มีอยู่แล้ว"
    
    # เลือก docker-compose file
    if [ "$MODE" = "prod" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
    else
        COMPOSE_FILE="docker-compose.yml"
    fi
    
    # ใช้ docker compose (v2) ถ้ามี
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    
    echo ""
    echo "🚀 เริ่มต้น services..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d
    
    echo ""
    echo "⏳ รอให้ services พร้อม..."
    sleep 5
    
    echo ""
    echo "📊 สถานะ services:"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" ps
    
    echo ""
    echo "✅ Services เริ่มต้นแล้ว!"
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
    echo "👤 Login: admin / admin123"
    echo ""
fi
