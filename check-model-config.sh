#!/bin/bash
# Script to check and fix AI_MODEL_NAME configuration

echo "=========================================="
echo "🔍 Checking AI_MODEL_NAME Configuration"
echo "=========================================="
echo ""

# Check backend/.env
echo "1. Checking backend/.env file..."
if [ -f "backend/.env" ]; then
    MODEL_IN_ENV=$(grep "^AI_MODEL_NAME=" backend/.env | cut -d '=' -f2 | tr -d ' ')
    echo "   ✅ Found: AI_MODEL_NAME=$MODEL_IN_ENV"
else
    echo "   ❌ backend/.env not found!"
    exit 1
fi

# Check what backend container sees
echo ""
echo "2. Checking backend container environment..."
CONTAINER_ENV=$(docker exec mnp-backend env 2>/dev/null | grep "^AI_MODEL_NAME=" | cut -d '=' -f2 | tr -d ' ')
if [ -n "$CONTAINER_ENV" ]; then
    echo "   ✅ Container env: AI_MODEL_NAME=$CONTAINER_ENV"
else
    echo "   ⚠️  AI_MODEL_NAME not found in container environment (will use .env or default)"
fi

# Check what Python Settings reads
echo ""
echo "3. Checking what Python Settings reads..."
PYTHON_MODEL=$(docker exec mnp-backend python -c "from app.core.settings import settings; print(settings.AI_MODEL_NAME)" 2>/dev/null)
if [ -n "$PYTHON_MODEL" ]; then
    echo "   ✅ Python Settings: AI_MODEL_NAME=$PYTHON_MODEL"
    
    if [ "$PYTHON_MODEL" != "$MODEL_IN_ENV" ]; then
        echo ""
        echo "   ⚠️  MISMATCH DETECTED!"
        echo "   - backend/.env has: $MODEL_IN_ENV"
        echo "   - Python Settings reads: $PYTHON_MODEL"
        echo ""
        echo "   This means environment variable is overriding .env file."
        echo "   Solution: Restart backend container to reload env_file"
    fi
else
    echo "   ❌ Could not read Python Settings"
fi

echo ""
echo "=========================================="
echo "💡 Recommendations:"
echo "=========================================="
echo ""
echo "If Python Settings shows 32b but .env has 14b:"
echo "  1. Restart backend: docker compose restart backend"
echo "  2. Wait 5 seconds: sleep 5"
echo "  3. Test again: curl -X POST 'http://10.4.15.167:8000/topology/test-llm' ..."
echo ""
echo "If still shows 32b after restart:"
echo "  1. Check for .env files in parent directories"
echo "  2. Check docker-compose.yml for environment: section"
echo "  3. Rebuild container: docker compose up -d --build backend"
echo ""
