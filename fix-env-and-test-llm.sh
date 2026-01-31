#!/bin/bash
# แก้ .env ให้ชี้ไปที่ Ollama ถูกต้อง → restart backend → ทดสอบ LLM
# ใช้: ./fix-env-and-test-llm.sh

set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

ENV_FILE="backend/.env"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

echo "=========================================="
echo "  1) ตรวจสอบ backend/.env"
echo "=========================================="
grep -E "^OLLAMA_|^TOPOLOGY" "$ENV_FILE" 2>/dev/null || true
echo ""

echo "=========================================="
echo "  2) Restart backend (โหลด .env ใหม่)"
echo "=========================================="
docker compose -f docker-compose.prod.yml up -d --build backend 2>&1
echo "รอ backend ขึ้น 15 วินาที..."
sleep 15
echo ""

echo "=========================================="
echo "  3) สถานะ LLM (health)"
echo "=========================================="
curl -s "$BACKEND_URL/health/llm" | python3 -m json.tool
echo ""

echo "=========================================="
echo "  4) ทดสอบยิง Hello ไปที่ LLM (รอได้ถึง 2 นาที)"
echo "=========================================="
curl -s --max-time 120 "$BACKEND_URL/ai/hello" | python3 -m json.tool
echo ""
echo "Done."
