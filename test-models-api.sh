#!/bin/bash
# Test different Ollama models using API endpoints

OLLAMA_URL="http://10.4.15.52:11434"
API_URL="http://localhost:8000"  # Backend API URL
AUTH_TOKEN=""  # Will be set if needed

echo "=========================================="
echo "Ollama Model Comparison Test (via API)"
echo "=========================================="
echo "Ollama Server: $OLLAMA_URL"
echo "API Server: $API_URL"
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

# Get a test project ID
echo "Getting test project from API..."
PROJECTS=$(curl -s "$API_URL/projects" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, list) and len(data) > 0:
        print(data[0].get('project_id') or data[0].get('id', ''))
    else:
        print('')
except:
    print('')
" 2>/dev/null)

if [ -z "$PROJECTS" ]; then
    echo "Error: No projects found. Please create a project and upload configs first."
    echo ""
    echo "You can test models manually by:"
    echo "1. Create a project and upload config files"
    echo "2. Update backend/.env: OLLAMA_MODEL=<model_name>"
    echo "3. Restart backend: docker compose -f docker-compose.prod.yml restart backend"
    echo "4. Test the LLM Analysis endpoints"
    exit 1
fi

PROJECT_ID=$(echo "$PROJECTS" | head -1)
echo "Using project: $PROJECT_ID"
echo ""

# Test each model
echo "=========================================="
echo "Testing Models"
echo "=========================================="
echo ""
echo "Note: This will temporarily change the model in the backend."
echo "After testing, you should update backend/.env with the best model."
echo ""

RESULTS_FILE="model_test_results_$(date +%Y%m%d_%H%M%S).txt"
echo "Results will be saved to: $RESULTS_FILE"
echo ""

for MODEL in $MODELS; do
    echo "----------------------------------------"
    echo "Testing Model: $MODEL"
    echo "----------------------------------------"
    
    # Update backend .env temporarily
    echo "  Updating backend configuration..."
    docker compose -f docker-compose.prod.yml exec -T backend bash -c "sed -i 's/^OLLAMA_MODEL=.*/OLLAMA_MODEL=$MODEL/' /app/.env" 2>/dev/null
    
    # Restart backend to apply changes
    echo "  Restarting backend..."
    docker compose -f docker-compose.prod.yml restart backend > /dev/null 2>&1
    sleep 5  # Wait for backend to start
    
    # Test Overview endpoint
    echo "  [1/2] Testing Overview analysis..."
    START_TIME=$(date +%s.%N)
    
    OVERVIEW_RESULT=$(curl -s -X POST "$API_URL/projects/$PROJECT_ID/analyze/overview" \
        -H "Content-Type: application/json" \
        -w "\n%{http_code}" 2>/dev/null | tail -1)
    
    # Poll for result
    OVERVIEW_SUCCESS=false
    OVERVIEW_TIME_VAL="N/A"
    for i in {1..24}; do  # Wait up to 2 minutes
        sleep 5
        RESULT=$(curl -s "$API_URL/projects/$PROJECT_ID/analyze/overview" 2>/dev/null)
        if echo "$RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); exit(0 if d.get('overview_text') else 1)" 2>/dev/null; then
            END_TIME=$(date +%s.%N)
            ELAPSED=$(echo "$END_TIME - $START_TIME" | bc)
            OVERVIEW_LEN=$(echo "$RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('overview_text', '')))" 2>/dev/null)
            echo "    ✓ Overview: ${ELAPSED}s (${OVERVIEW_LEN} chars)"
            OVERVIEW_SUCCESS=true
            OVERVIEW_TIME_VAL=$ELAPSED
            break
        fi
    done
    
    if [ "$OVERVIEW_SUCCESS" = false ]; then
        echo "    ✗ Overview: Timeout or failed"
    fi
    
    sleep 2
    
    # Test Recommendations endpoint
    echo "  [2/2] Testing Recommendations analysis..."
    START_TIME=$(date +%s.%N)
    
    REC_RESULT=$(curl -s -X POST "$API_URL/projects/$PROJECT_ID/analyze/recommendations" \
        -H "Content-Type: application/json" \
        -w "\n%{http_code}" 2>/dev/null | tail -1)
    
    # Poll for result
    REC_SUCCESS=false
    REC_TIME_VAL="N/A"
    for i in {1..24}; do  # Wait up to 2 minutes
        sleep 5
        RESULT=$(curl -s "$API_URL/projects/$PROJECT_ID/analyze/recommendations" 2>/dev/null)
        if echo "$RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); exit(0 if d.get('generated_at') else 1)" 2>/dev/null; then
            END_TIME=$(date +%s.%N)
            ELAPSED=$(echo "$END_TIME - $START_TIME" | bc)
            REC_COUNT=$(echo "$RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('recommendations', [])))" 2>/dev/null)
            echo "    ✓ Recommendations: ${ELAPSED}s (${REC_COUNT} recommendations)"
            REC_SUCCESS=true
            REC_TIME_VAL=$ELAPSED
            break
        fi
    done
    
    if [ "$REC_SUCCESS" = false ]; then
        echo "    ✗ Recommendations: Timeout or failed"
    fi
    
    # Save results
    echo "$MODEL|$OVERVIEW_SUCCESS|$OVERVIEW_TIME_VAL|$REC_SUCCESS|$REC_TIME_VAL" >> "$RESULTS_FILE"
    
    echo ""
    sleep 3
done

# Restore original model
ORIGINAL_MODEL="deepseek-r1:7b"
docker compose -f docker-compose.prod.yml exec -T backend bash -c "sed -i 's/^OLLAMA_MODEL=.*/OLLAMA_MODEL=$ORIGINAL_MODEL/' /app/.env" 2>/dev/null
docker compose -f docker-compose.prod.yml restart backend > /dev/null 2>&1

# Print summary
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo ""
printf "%-30s %-20s %-20s %-15s\n" "Model" "Overview" "Recommendations" "Avg Time"
echo "----------------------------------------------------------------------------"

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
    
    printf "%-30s %-20s %-20s %-15s\n" "$MODEL" "$OV_STATUS" "$REC_STATUS" "$AVG_TIME"
done < "$RESULTS_FILE"

echo ""
echo "Detailed results saved to: $RESULTS_FILE"
echo ""
echo "To use the best model, update backend/.env:"
echo "OLLAMA_MODEL=<best_model_name>"
echo ""
echo "Then restart backend:"
echo "docker compose -f docker-compose.prod.yml restart backend"
