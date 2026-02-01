#!/bin/bash
# ตรวจสอบ backend logs เพื่อหา error
# ใช้: ./check-backend-logs.sh

echo "=========================================="
echo "  Backend Logs (last 100 lines)"
echo "=========================================="
docker compose -f docker-compose.prod.yml logs backend --tail 100 2>&1 | grep -i "error\|exception\|traceback\|failed" || echo "No errors found in last 100 lines"

echo ""
echo "=========================================="
echo "  Frontend Logs (last 50 lines)"
echo "=========================================="
docker compose -f docker-compose.prod.yml logs frontend --tail 50 2>&1 | grep -i "error\|exception\|failed" || echo "No errors found in last 50 lines"

echo ""
echo "=========================================="
echo "  All Recent Logs (last 30 lines)"
echo "=========================================="
docker compose -f docker-compose.prod.yml logs --tail 30 2>&1
