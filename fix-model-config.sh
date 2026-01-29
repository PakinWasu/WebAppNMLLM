#!/bin/bash
# Script to fix AI_MODEL_NAME configuration issue

echo "=========================================="
echo "🔧 Fixing AI_MODEL_NAME Configuration"
echo "=========================================="
echo ""

# Ensure backend/.env has 14b
echo "1. Checking backend/.env..."
if [ -f "backend/.env" ]; then
    if grep -q "AI_MODEL_NAME=qwen2.5-coder:14b" backend/.env; then
        echo "   ✅ backend/.env already has 14b"
    else
        echo "   ⚠️  Updating backend/.env to use 14b..."
        sed -i 's/^AI_MODEL_NAME=.*/AI_MODEL_NAME=qwen2.5-coder:14b/' backend/.env
        echo "   ✅ Updated"
    fi
else
    echo "   ❌ backend/.env not found! Creating from .env.example..."
    cp backend/.env.example backend/.env
    sed -i 's/^AI_MODEL_NAME=.*/AI_MODEL_NAME=qwen2.5-coder:14b/' backend/.env
fi

# Stop and remove backend container to force reload env_file
echo ""
echo "2. Stopping backend container..."
docker compose stop backend

echo ""
echo "3. Removing backend container..."
docker compose rm -f backend

echo ""
echo "4. Starting backend container (will reload env_file)..."
docker compose up -d backend

echo ""
echo "5. Waiting for backend to start..."
sleep 10

echo ""
echo "6. Checking Python Settings..."
PYTHON_MODEL=$(docker exec mnp-backend python -c "from app.core.settings import settings; print(settings.AI_MODEL_NAME)" 2>/dev/null)
if [ -n "$PYTHON_MODEL" ]; then
    echo "   ✅ Python Settings now reads: AI_MODEL_NAME=$PYTHON_MODEL"
    if [ "$PYTHON_MODEL" = "qwen2.5-coder:14b" ]; then
        echo ""
        echo "   ✅ SUCCESS! Backend is now using 14b model"
    else
        echo ""
        echo "   ⚠️  Still showing $PYTHON_MODEL - may need to check environment variables"
    fi
else
    echo "   ❌ Could not read Python Settings"
fi

echo ""
echo "=========================================="
echo "✅ Fix complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Pre-load 14b model: docker exec mnp-ollama ollama run qwen2.5-coder:14b 'hello'"
echo "  2. Test: curl -X POST 'http://10.4.15.167:8000/topology/test-llm' ..."
echo ""
