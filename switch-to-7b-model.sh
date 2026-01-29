#!/bin/bash
# Script to switch to qwen2.5-coder:7b model

echo "=========================================="
echo "🔄 Switching to qwen2.5-coder:7b Model"
echo "=========================================="
echo ""

# 1. Pull model 7b
echo "1. Pulling qwen2.5-coder:7b model..."
docker exec mnp-ollama ollama pull qwen2.5-coder:7b
if [ $? -eq 0 ]; then
    echo "   ✅ Model pulled successfully"
else
    echo "   ❌ Failed to pull model"
    exit 1
fi

echo ""
echo "2. Pre-loading model (warming up)..."
docker exec mnp-ollama ollama run qwen2.5-coder:7b "hello"
echo "   ✅ Model pre-loaded"

echo ""
echo "3. Stopping backend..."
docker compose stop backend

echo ""
echo "4. Removing backend container to reload config..."
docker compose rm -f backend

echo ""
echo "5. Starting backend..."
docker compose up -d backend

echo ""
echo "6. Waiting for backend to start..."
sleep 10

echo ""
echo "7. Verifying configuration..."
PYTHON_MODEL=$(docker exec mnp-backend python -c "from app.core.settings import settings; print(settings.AI_MODEL_NAME)" 2>/dev/null)
if [ -n "$PYTHON_MODEL" ]; then
    echo "   ✅ Backend is using: $PYTHON_MODEL"
    if [ "$PYTHON_MODEL" = "qwen2.5-coder:7b" ]; then
        echo ""
        echo "   ✅ SUCCESS! Backend is now using 7b model"
    else
        echo ""
        echo "   ⚠️  Backend is using $PYTHON_MODEL (expected 7b)"
    fi
else
    echo "   ❌ Could not verify configuration"
fi

echo ""
echo "=========================================="
echo "✅ Switch complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Test LLM: curl -X POST 'http://10.4.15.167:8000/topology/test-llm' ..."
echo "  2. Generate topology: POST /projects/{project_id}/topology/generate"
echo ""
