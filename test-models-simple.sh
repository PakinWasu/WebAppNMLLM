#!/bin/bash
# Simple script to test different Ollama models

OLLAMA_URL="http://10.4.15.52:11434"
PROJECT_ID=""

echo "=========================================="
echo "Ollama Model Comparison Test"
echo "=========================================="
echo "Ollama Server: $OLLAMA_URL"
echo ""

# Get available models
echo "Fetching available models..."
MODELS=$(curl -s "$OLLAMA_URL/api/tags" | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = [m['name'] for m in data.get('models', [])]
print(' '.join(models))
" 2>/dev/null)

if [ -z "$MODELS" ]; then
    echo "Error: Cannot connect to Ollama server or no models found"
    exit 1
fi

echo "Found models:"
for model in $MODELS; do
    echo "  - $model"
done
echo ""

# Get a test project ID from database
echo "Getting test project from database..."
PROJECT_ID=$(docker compose -f docker-compose.prod.yml exec -T backend python3 -c "
import sys
sys.path.insert(0, '/app')
import asyncio
from app.db.mongo import db

async def get_project():
    project = await db()['projects'].find_one(
        {'summaryRows': {'\$exists': True, '\$ne': []}},
        sort=[('updated_at', -1)]
    )
    if project:
        return str(project.get('project_id') or project.get('_id'))
    return None

pid = asyncio.run(get_project())
print(pid if pid else '')
" 2>/dev/null | head -1)

if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "None" ]; then
    echo "Error: No project found with devices. Please upload some configs first."
    exit 1
fi

echo "Using project: $PROJECT_ID"
echo ""

# Test each model
echo "=========================================="
echo "Testing Models"
echo "=========================================="
echo ""

RESULTS_FILE="model_test_results_$(date +%Y%m%d_%H%M%S).txt"
echo "Results will be saved to: $RESULTS_FILE"
echo ""

for MODEL in $MODELS; do
    echo "----------------------------------------"
    echo "Testing Model: $MODEL"
    echo "----------------------------------------"
    
    # Test Overview
    echo "  [1/2] Testing Overview analysis..."
    START_TIME=$(date +%s.%N)
    
    RESULT=$(docker compose -f docker-compose.prod.yml exec -T backend python3 -c "
import sys
import os
import asyncio
import time
sys.path.insert(0, '/app')

os.environ['OLLAMA_MODEL'] = '$MODEL'

from app.db.mongo import db
from app.services.llm_service import LLMService

async def test():
    llm_service = LLMService()
    llm_service.model_name = '$MODEL'
    
    # Get devices
    devices = await db()['devices'].find({'project_id': '$PROJECT_ID'}).to_list(length=5)
    devices_data = []
    for d in devices:
        devices_data.append({
            'device_id': d.get('device_id'),
            'hostname': d.get('hostname', 'Unknown'),
            'parsed_config': d.get('parsed_config', {})
        })
    
    if not devices_data:
        print('ERROR: No devices found')
        return
    
    start = time.time()
    try:
        result = await llm_service.analyze_project_overview(
            devices_data=devices_data,
            project_id='$PROJECT_ID'
        )
        elapsed = time.time() - start
        print(f'SUCCESS|{elapsed:.2f}|{len(result.get(\"overview_text\", \"\"))}')
    except Exception as e:
        elapsed = time.time() - start
        print(f'FAILED|{elapsed:.2f}|{str(e)}')

asyncio.run(test())
" 2>&1 | tail -1)
    
    END_TIME=$(date +%s.%N)
    TOTAL_TIME=$(echo "$END_TIME - $START_TIME" | bc)
    
    if echo "$RESULT" | grep -q "SUCCESS"; then
        OVERVIEW_TIME=$(echo "$RESULT" | cut -d'|' -f2)
        OVERVIEW_LEN=$(echo "$RESULT" | cut -d'|' -f3)
        echo "    ✓ Overview: ${OVERVIEW_TIME}s (${OVERVIEW_LEN} chars)"
        OVERVIEW_SUCCESS=true
        OVERVIEW_TIME_VAL=$OVERVIEW_TIME
    else
        ERROR=$(echo "$RESULT" | cut -d'|' -f3)
        echo "    ✗ Overview failed: $ERROR"
        OVERVIEW_SUCCESS=false
        OVERVIEW_TIME_VAL="N/A"
    fi
    
    sleep 2
    
    # Test Recommendations
    echo "  [2/2] Testing Recommendations analysis..."
    START_TIME=$(date +%s.%N)
    
    RESULT=$(docker compose -f docker-compose.prod.yml exec -T backend python3 -c "
import sys
import os
import asyncio
import time
sys.path.insert(0, '/app')

os.environ['OLLAMA_MODEL'] = '$MODEL'

from app.db.mongo import db
from app.services.llm_service import LLMService

async def test():
    llm_service = LLMService()
    llm_service.model_name = '$MODEL'
    
    # Get devices
    devices = await db()['devices'].find({'project_id': '$PROJECT_ID'}).to_list(length=5)
    devices_data = []
    for d in devices:
        devices_data.append({
            'device_id': d.get('device_id'),
            'hostname': d.get('hostname', 'Unknown'),
            'parsed_config': d.get('parsed_config', {})
        })
    
    if not devices_data:
        print('ERROR: No devices found')
        return
    
    start = time.time()
    try:
        result = await llm_service.analyze_project_recommendations(
            devices_data=devices_data,
            project_id='$PROJECT_ID'
        )
        elapsed = time.time() - start
        recs = result.get('recommendations', [])
        print(f'SUCCESS|{elapsed:.2f}|{len(recs)}')
    except Exception as e:
        elapsed = time.time() - start
        print(f'FAILED|{elapsed:.2f}|{str(e)}')

asyncio.run(test())
" 2>&1 | tail -1)
    
    END_TIME=$(date +%s.%N)
    TOTAL_TIME=$(echo "$END_TIME - $START_TIME" | bc)
    
    if echo "$RESULT" | grep -q "SUCCESS"; then
        REC_TIME=$(echo "$RESULT" | cut -d'|' -f2)
        REC_COUNT=$(echo "$RESULT" | cut -d'|' -f3)
        echo "    ✓ Recommendations: ${REC_TIME}s (${REC_COUNT} recommendations)"
        REC_SUCCESS=true
        REC_TIME_VAL=$REC_TIME
    else
        ERROR=$(echo "$RESULT" | cut -d'|' -f3)
        echo "    ✗ Recommendations failed: $ERROR"
        REC_SUCCESS=false
        REC_TIME_VAL="N/A"
    fi
    
    # Save results
    echo "$MODEL|$OVERVIEW_SUCCESS|$OVERVIEW_TIME_VAL|$REC_SUCCESS|$REC_TIME_VAL" >> "$RESULTS_FILE"
    
    echo ""
    sleep 3
done

# Print summary
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo ""
printf "%-30s %-15s %-15s %-15s\n" "Model" "Overview" "Recommendations" "Avg Time"
echo "----------------------------------------"

while IFS='|' read -r MODEL OV_SUCCESS OV_TIME REC_SUCCESS REC_TIME; do
    OV_STATUS="✓ ${OV_TIME}s"
    if [ "$OV_SUCCESS" != "true" ]; then
        OV_STATUS="✗ FAILED"
    fi
    
    REC_STATUS="✓ ${REC_TIME}s"
    if [ "$REC_SUCCESS" != "true" ]; then
        REC_STATUS="✗ FAILED"
    fi
    
    AVG_TIME="N/A"
    if [ "$OV_SUCCESS" = "true" ] && [ "$REC_SUCCESS" = "true" ]; then
        AVG_TIME=$(echo "scale=2; ($OV_TIME + $REC_TIME) / 2" | bc)
        AVG_TIME="${AVG_TIME}s"
    fi
    
    printf "%-30s %-15s %-15s %-15s\n" "$MODEL" "$OV_STATUS" "$REC_STATUS" "$AVG_TIME"
done < "$RESULTS_FILE"

echo ""
echo "Detailed results saved to: $RESULTS_FILE"
echo ""
echo "To use the best model, update backend/.env:"
echo "OLLAMA_MODEL=<best_model_name>"
