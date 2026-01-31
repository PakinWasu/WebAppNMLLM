#!/bin/bash
# อัปเดตแล้ว restart Docker เสมอ (รวมถึงเมื่อแก้ LLM / .env / โค้ด backend)
# ใช้: ./update-and-restart.sh
# หรือ pull จาก git ก่อนแล้วค่อย restart: ./update-and-restart.sh --pull

set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

COMPOSE_FILE="docker-compose.prod.yml"
PULL=false
[[ "$1" == "--pull" ]] && PULL=true

echo "=========================================="
echo "  WebAppNMLLM - Update & Restart Docker"
echo "=========================================="
echo ""

if [[ "$PULL" == "true" ]] && [[ -d ".git" ]]; then
    echo "Pulling latest changes..."
    git pull origin main || true
    echo ""
fi

echo "Restarting containers (build if needed)..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo ""
echo "Done. Containers:"
docker compose -f "$COMPOSE_FILE" ps
echo ""
echo "ดู logs: docker compose -f $COMPOSE_FILE logs -f"
