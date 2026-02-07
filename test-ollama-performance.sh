#!/bin/bash
# Test Ollama Server Performance
# Usage: ./test-ollama-performance.sh [OLLAMA_URL] [MODEL_NAME]

OLLAMA_URL=${1:-"http://10.4.15.152:11434"}
MODEL_NAME=${2:-"qwen2.5-coder:7b"}

echo "=========================================="
echo "Ollama Server Performance Test"
echo "=========================================="
echo ""
echo "Server: $OLLAMA_URL"
echo "Model: $MODEL_NAME"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test 1: Connection Test
echo -e "${CYAN}[Test 1] Connection Test${NC}"
echo "Testing connection to Ollama server..."
if curl -s --max-time 5 "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connection successful${NC}"
else
    echo -e "${RED}✗ Connection failed${NC}"
    echo "Cannot reach $OLLAMA_URL"
    exit 1
fi
echo ""

# Test 2: List Available Models
echo -e "${CYAN}[Test 2] Available Models${NC}"
MODELS_JSON=$(curl -s --max-time 5 "$OLLAMA_URL/api/tags")
if [ $? -eq 0 ]; then
    echo "$MODELS_JSON" | python3 -m json.tool 2>/dev/null || echo "$MODELS_JSON"
    MODEL_COUNT=$(echo "$MODELS_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('models', [])))" 2>/dev/null || echo "0")
    echo -e "${GREEN}✓ Found $MODEL_COUNT model(s)${NC}"
else
    echo -e "${RED}✗ Failed to list models${NC}"
fi
echo ""

# Test 3: Check if Model Exists
echo -e "${CYAN}[Test 3] Model Availability${NC}"
MODEL_EXISTS=$(echo "$MODELS_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); models=[m['name'] for m in data.get('models', [])]; print('yes' if '$MODEL_NAME' in models else 'no')" 2>/dev/null || echo "no")
if [ "$MODEL_EXISTS" = "yes" ]; then
    echo -e "${GREEN}✓ Model '$MODEL_NAME' is available${NC}"
else
    echo -e "${RED}✗ Model '$MODEL_NAME' not found${NC}"
    echo "Available models:"
    echo "$MODELS_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); [print(f\"  - {m['name']}\") for m in data.get('models', [])]" 2>/dev/null || echo "  (unable to parse)"
    exit 1
fi
echo ""

# Test 4: Simple Generation Test (Short)
echo -e "${CYAN}[Test 4] Simple Generation Test (Short Prompt)${NC}"
echo "Sending short prompt: 'Say OK'"
START_TIME=$(date +%s.%N)
RESPONSE=$(curl -s --max-time 30 -X POST "$OLLAMA_URL/api/generate" \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"$MODEL_NAME\", \"prompt\": \"Say OK\", \"stream\": false}")
END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc 2>/dev/null || echo "0")

if echo "$RESPONSE" | grep -q '"response"'; then
    RESPONSE_TEXT=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('response', '')[:100])" 2>/dev/null || echo "OK")
    echo -e "${GREEN}✓ Response received${NC}"
    echo "  Response: $RESPONSE_TEXT"
    echo "  Duration: ${DURATION}s"
    if (( $(echo "$DURATION > 5.0" | bc -l 2>/dev/null || echo 0) )); then
        echo -e "  ${YELLOW}⚠ Slow response (>5s)${NC}"
    fi
else
    echo -e "${RED}✗ Generation failed${NC}"
    echo "  Response: $RESPONSE"
fi
echo ""

# Test 5: Chat API Test (Like Backend Uses)
echo -e "${CYAN}[Test 5] Chat API Test (Backend Format)${NC}"
echo "Testing chat API with system/user messages..."
START_TIME=$(date +%s.%N)
CHAT_RESPONSE=$(curl -s --max-time 60 -X POST "$OLLAMA_URL/api/chat" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"$MODEL_NAME\",
        \"messages\": [
            {\"role\": \"system\", \"content\": \"You are a helpful assistant.\"},
            {\"role\": \"user\", \"content\": \"Say hello in one word.\"}
        ],
        \"stream\": false
    }")
END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc 2>/dev/null || echo "0")

if echo "$CHAT_RESPONSE" | grep -q '"message"'; then
    CHAT_TEXT=$(echo "$CHAT_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('message', {}).get('content', '')[:100])" 2>/dev/null || echo "Hello")
    echo -e "${GREEN}✓ Chat API working${NC}"
    echo "  Response: $CHAT_TEXT"
    echo "  Duration: ${DURATION}s"
    
    # Extract token counts
    PROMPT_TOKENS=$(echo "$CHAT_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('prompt_eval_count', 0))" 2>/dev/null || echo "0")
    EVAL_TOKENS=$(echo "$CHAT_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('eval_count', 0))" 2>/dev/null || echo "0")
    echo "  Prompt tokens: $PROMPT_TOKENS"
    echo "  Completion tokens: $EVAL_TOKENS"
    
    if (( $(echo "$DURATION > 10.0" | bc -l 2>/dev/null || echo 0) )); then
        echo -e "  ${YELLOW}⚠ Slow response (>10s)${NC}"
    fi
else
    echo -e "${RED}✗ Chat API failed${NC}"
    echo "  Response: $CHAT_RESPONSE"
fi
echo ""

# Test 6: Performance Test (Multiple Requests)
echo -e "${CYAN}[Test 6] Performance Test (3 Sequential Requests)${NC}"
TOTAL_TIME=0
SUCCESS_COUNT=0
for i in {1..3}; do
    echo -n "  Request $i: "
    START_TIME=$(date +%s.%N)
    TEST_RESPONSE=$(curl -s --max-time 30 -X POST "$OLLAMA_URL/api/generate" \
        -H "Content-Type: application/json" \
        -d "{\"model\": \"$MODEL_NAME\", \"prompt\": \"Count to $i\", \"stream\": false}")
    END_TIME=$(date +%s.%N)
    DURATION=$(echo "$END_TIME - $START_TIME" | bc 2>/dev/null || echo "0")
    
    if echo "$TEST_RESPONSE" | grep -q '"response"'; then
        echo -e "${GREEN}✓${NC} ${DURATION}s"
        TOTAL_TIME=$(echo "$TOTAL_TIME + $DURATION" | bc 2>/dev/null || echo "$TOTAL_TIME")
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "${RED}✗ Failed${NC}"
    fi
done

if [ $SUCCESS_COUNT -gt 0 ]; then
    AVG_TIME=$(echo "scale=2; $TOTAL_TIME / $SUCCESS_COUNT" | bc 2>/dev/null || echo "0")
    echo "  Average: ${AVG_TIME}s"
    echo -e "${GREEN}✓ Performance test completed ($SUCCESS_COUNT/3 successful)${NC}"
else
    echo -e "${RED}✗ All requests failed${NC}"
fi
echo ""

# Test 7: Test from Backend Container (if running)
echo -e "${CYAN}[Test 7] Test from Backend Container${NC}"
if docker ps | grep -q "mnp-backend-prod"; then
    echo "Testing connection from backend container..."
    BACKEND_TEST=$(docker exec mnp-backend-prod python3 -c "
import os, httpx
url = os.getenv('OLLAMA_BASE_URL', 'http://10.4.15.52:11434').rstrip('/')
model = os.getenv('OLLAMA_MODEL', 'deepseek-r1:7b')
try:
    r = httpx.get(url + '/api/tags', timeout=5.0)
    print('Connection:', 'OK' if r.status_code == 200 else f'FAIL ({r.status_code})')
    if r.status_code == 200:
        data = r.json()
        models = [m['name'] for m in data.get('models', [])]
        print('Model available:', 'YES' if model in models else 'NO')
        print('Available models:', ', '.join(models[:5]))
except Exception as e:
    print('Error:', str(e))
" 2>&1)
    echo "$BACKEND_TEST"
    if echo "$BACKEND_TEST" | grep -q "Connection: OK"; then
        echo -e "${GREEN}✓ Backend can reach Ollama server${NC}"
    else
        echo -e "${RED}✗ Backend cannot reach Ollama server${NC}"
    fi
else
    echo "Backend container not running, skipping container test"
fi
echo ""

# Summary
echo "=========================================="
echo -e "${CYAN}Summary${NC}"
echo "=========================================="
echo "Server: $OLLAMA_URL"
echo "Model: $MODEL_NAME"
echo ""
echo "Recommendations:"
if [ "$MODEL_EXISTS" = "yes" ]; then
    echo -e "  ${GREEN}✓ Model is available${NC}"
else
    echo -e "  ${RED}✗ Model not found${NC}"
fi

if [ $SUCCESS_COUNT -gt 0 ]; then
    echo -e "  ${GREEN}✓ API is responding${NC}"
    if (( $(echo "$AVG_TIME < 5.0" | bc -l 2>/dev/null || echo 0) )); then
        echo -e "  ${GREEN}✓ Response time is good (<5s avg)${NC}"
    elif (( $(echo "$AVG_TIME < 10.0" | bc -l 2>/dev/null || echo 0) )); then
        echo -e "  ${YELLOW}⚠ Response time is acceptable (5-10s avg)${NC}"
    else
        echo -e "  ${RED}✗ Response time is slow (>10s avg)${NC}"
    fi
else
    echo -e "  ${RED}✗ API is not responding correctly${NC}"
fi
echo ""
