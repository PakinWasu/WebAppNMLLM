#!/bin/bash
# Script to force Ollama to use 7b model and unload other models

echo "=========================================="
echo "🔄 Forcing Ollama to use 7b model"
echo "=========================================="
echo ""

# 1. Check current models
echo "1. Checking available models..."
docker exec mnp-ollama ollama list

echo ""
echo "2. Pulling 7b model (if not already pulled)..."
docker exec mnp-ollama ollama pull qwen2.5-coder:7b

echo ""
echo "3. Pre-loading 7b model (this will unload other models)..."
docker exec mnp-ollama ollama run qwen2.5-coder:7b "test" > /dev/null 2>&1
echo "   ✅ 7b model loaded"

echo ""
echo "4. Verifying 7b model is ready..."
docker exec mnp-ollama ollama run qwen2.5-coder:7b "hello" | head -1
echo "   ✅ 7b model is ready"

echo ""
echo "5. Restarting backend to reload config..."
docker compose restart backend

echo ""
echo "6. Waiting for backend to start..."
sleep 10

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "Test with:"
echo "  curl -X POST 'http://10.4.15.167:8000/topology/test-llm' -H 'Authorization: Bearer \$TOKEN' | jq"
echo ""
