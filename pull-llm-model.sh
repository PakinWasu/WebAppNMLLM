#!/bin/bash

# สคริปต์สำหรับ pull โมเดล LLM อัตโนมัติ
# Usage: ./pull-llm-model.sh [model_name]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# อ่านชื่อโมเดลจาก .env หรือใช้ค่าที่ส่งมา
if [ -n "$1" ]; then
    MODEL_NAME="$1"
else
    if [ -f "backend/.env" ]; then
        MODEL_NAME=$(grep AI_MODEL_NAME backend/.env | cut -d '=' -f2 | tr -d ' ')
    else
        MODEL_NAME="qwen2.5-coder:32b"
    fi
fi

echo "=========================================="
echo "🤖 Pull LLM Model: $MODEL_NAME"
echo "=========================================="
echo ""

# หา Ollama container
OLLAMA_CONTAINER=""
if docker ps | grep -q "mnp-ollama-prod"; then
    OLLAMA_CONTAINER="mnp-ollama-prod"
elif docker ps | grep -q "mnp-ollama"; then
    OLLAMA_CONTAINER="mnp-ollama"
fi

if [ -z "$OLLAMA_CONTAINER" ]; then
    echo "❌ ไม่พบ Ollama container!"
    echo "   กรุณา start services ก่อนด้วย: ./setup-and-start.sh"
    exit 1
fi

echo "✅ พบ Ollama container: $OLLAMA_CONTAINER"
echo ""

# ตรวจสอบว่าโมเดลมีอยู่แล้วหรือยัง
echo "🔍 ตรวจสอบโมเดลที่มีอยู่..."
if docker exec "$OLLAMA_CONTAINER" ollama list 2>/dev/null | grep -q "$MODEL_NAME"; then
    echo "✅ โมเดล $MODEL_NAME มีอยู่แล้ว"
    echo ""
    echo "📋 รายการโมเดลทั้งหมด:"
    docker exec "$OLLAMA_CONTAINER" ollama list
    exit 0
fi

# Pull โมเดล
echo "📥 กำลังดาวน์โหลดโมเดล $MODEL_NAME..."
if [[ "$MODEL_NAME" == *"32b"* ]] || [[ "$MODEL_NAME" == *"32B"* ]]; then
    echo "   ⚠️  โมเดลขนาดใหญ่ (~18GB) อาจใช้เวลานานมากในการดาวน์โหลด"
    echo "   ⚠️  ต้องการ RAM ~16-20GB และ Disk space ~18GB"
elif [[ "$MODEL_NAME" == *"14b"* ]] || [[ "$MODEL_NAME" == *"14B"* ]]; then
    echo "   ⚠️  โมเดลขนาดกลาง (~8GB) อาจใช้เวลานาน"
    echo "   ⚠️  ต้องการ RAM ~8-10GB"
else
    echo "   ⚠️  อาจใช้เวลานาน (ขึ้นอยู่กับขนาดโมเดลและความเร็วอินเทอร์เน็ต)"
fi
echo ""

docker exec "$OLLAMA_CONTAINER" ollama pull "$MODEL_NAME"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ดาวน์โหลดโมเดล $MODEL_NAME เสร็จสิ้น!"
    echo ""
    echo "📋 รายการโมเดลทั้งหมด:"
    docker exec "$OLLAMA_CONTAINER" ollama list
else
    echo ""
    echo "❌ ไม่สามารถดาวน์โหลดโมเดลได้"
    exit 1
fi
