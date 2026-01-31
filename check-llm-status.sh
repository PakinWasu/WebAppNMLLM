#!/bin/bash
# ตรวจสอบสถานะ LLM: เชื่อมต่อได้ไหม + ทดสอบยิง Hello ให้ตอบกลับ
# ใช้: ./check-llm-status.sh [base_url]
# base_url  default = http://localhost:8000

BASE="${1:-http://localhost:8000}"
echo "=========================================="
echo "  ตรวจสอบสถานะ LLM (Backend: $BASE)"
echo "=========================================="
echo ""

echo "1) Health - สถานะการเชื่อมต่อ Ollama และโมเดล"
echo "---"
curl -s "$BASE/health/llm" | python3 -m json.tool 2>/dev/null || curl -s "$BASE/health/llm"
echo ""
echo ""

echo "2) ทดสอบยิง Hello ไปที่ LLM (รอได้ถึง 2 นาที)..."
echo "---"
curl -s --max-time 120 "$BASE/ai/hello" | python3 -m json.tool 2>/dev/null || curl -s --max-time 120 "$BASE/ai/hello"
echo ""
