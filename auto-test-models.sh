#!/bin/bash
# Automatically test all Ollama models and select the best one

set -e

OLLAMA_URL="http://10.4.15.52:11434"
BACKEND_ENV="/home/nmp/Downloads/WebAppNMLLM/backend/.env"
COMPOSE_FILE="docker-compose.prod.yml"
API_URL="http://localhost:8000"

echo "=========================================="
echo "Automatic Ollama Model Testing"
echo "=========================================="
echo "Ollama Server: $OLLAMA_URL"
echo "This will take several minutes..."
echo ""

# Get available models
echo "[1/5] Fetching available models..."
MODELS=$(curl -s "$OLLAMA_URL/api/tags" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    models = [m['name'] for m in data.get('models', [])]
    print(' '.join(models))
except:
    print('')
" 2>/dev/null)

if [ -z "$MODELS" ]; then
    echo "Error: Cannot connect to Ollama server"
    exit 1
fi

echo "Found models:"
for model in $MODELS; do
    echo "  - $model"
done
echo ""

# Get test project
echo "[2/5] Getting test project..."
PROJECT_ID=$(docker compose -f "$COMPOSE_FILE" exec -T backend python3 -c "
import sys, asyncio
sys.path.insert(0, '/app')
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
    echo "Error: No project found. Creating a test project..."
    # Try to get any project
    PROJECT_ID=$(docker compose -f "$COMPOSE_FILE" exec -T backend python3 -c "
import sys, asyncio
sys.path.insert(0, '/app')
from app.db.mongo import db

async def get_any_project():
    project = await db()['projects'].find_one(sort=[('updated_at', -1)])
    if project:
        return str(project.get('project_id') or project.get('_id'))
    return None

pid = asyncio.run(get_any_project())
print(pid if pid else '')
" 2>/dev/null | head -1)
    
    if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "None" ]; then
        echo "Error: Cannot find any project. Please create a project first."
        exit 1
    fi
fi

echo "Using project: $PROJECT_ID"
echo ""

# Backup original model
ORIGINAL_MODEL=$(grep "^OLLAMA_MODEL=" "$BACKEND_ENV" | cut -d'=' -f2 || echo "deepseek-r1:7b")
echo "Current model: $ORIGINAL_MODEL"
echo ""

# Results file
RESULTS_FILE="model_test_results_$(date +%Y%m%d_%H%M%S).json"
echo "Results will be saved to: $RESULTS_FILE"
echo ""

# Test function
test_model() {
    local MODEL=$1
    local PROJECT_ID=$2
    
    echo "  Testing $MODEL..."
    
    # Update .env
    sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$MODEL|" "$BACKEND_ENV"
    
    # Restart backend
    cd /home/nmp/Downloads/WebAppNMLLM
    docker compose -f "$COMPOSE_FILE" restart backend > /dev/null 2>&1
    
    # Wait for backend
    echo "    Waiting for backend to restart..."
    sleep 15
    
    # Check backend health
    for i in {1..30}; do
        if curl -s "$API_URL/docs" > /dev/null 2>&1 || \
           curl -s "$API_URL/health" > /dev/null 2>&1; then
            break
        fi
        sleep 2
    done
    
    # Test Overview
    echo "    Testing Overview analysis..."
    OVERVIEW_START=$(date +%s.%N)
    
    # Trigger analysis
    curl -s -X POST "$API_URL/projects/$PROJECT_ID/analyze/overview" \
        -H "Content-Type: application/json" > /dev/null 2>&1
    
    # Poll for result
    OVERVIEW_SUCCESS=false
    OVERVIEW_TIME="N/A"
    OVERVIEW_LEN=0
    
    for i in {1..30}; do
        sleep 5
        RESULT=$(curl -s "$API_URL/projects/$PROJECT_ID/analyze/overview" 2>/dev/null)
        if echo "$RESULT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    if d.get('overview_text'):
        print('SUCCESS')
        print(len(d.get('overview_text', '')))
    else:
        print('WAITING')
except:
    print('WAITING')
" 2>/dev/null | head -1 | grep -q "SUCCESS"; then
            OVERVIEW_END=$(date +%s.%N)
            OVERVIEW_TIME=$(echo "$OVERVIEW_END - $OVERVIEW_START" | bc)
            OVERVIEW_LEN=$(echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(len(d.get('overview_text', '')))
" 2>/dev/null)
            OVERVIEW_SUCCESS=true
            echo "      ✓ Overview: ${OVERVIEW_TIME}s (${OVERVIEW_LEN} chars)"
            break
        fi
    done
    
    if [ "$OVERVIEW_SUCCESS" = false ]; then
        echo "      ✗ Overview: Timeout"
    fi
    
    sleep 3
    
    # Test Recommendations
    echo "    Testing Recommendations analysis..."
    REC_START=$(date +%s.%N)
    
    # Trigger analysis
    curl -s -X POST "$API_URL/projects/$PROJECT_ID/analyze/recommendations" \
        -H "Content-Type: application/json" > /dev/null 2>&1
    
    # Poll for result
    REC_SUCCESS=false
    REC_TIME="N/A"
    REC_COUNT=0
    
    for i in {1..30}; do
        sleep 5
        RESULT=$(curl -s "$API_URL/projects/$PROJECT_ID/analyze/recommendations" 2>/dev/null)
        if echo "$RESULT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    if d.get('generated_at'):
        print('SUCCESS')
        print(len(d.get('recommendations', [])))
    else:
        print('WAITING')
except:
    print('WAITING')
" 2>/dev/null | head -1 | grep -q "SUCCESS"; then
            REC_END=$(date +%s.%N)
            REC_TIME=$(echo "$REC_END - $REC_START" | bc)
            REC_COUNT=$(echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(len(d.get('recommendations', [])))
" 2>/dev/null)
            REC_SUCCESS=true
            echo "      ✓ Recommendations: ${REC_TIME}s (${REC_COUNT} recommendations)"
            break
        fi
    done
    
    if [ "$REC_SUCCESS" = false ]; then
        echo "      ✗ Recommendations: Timeout"
    fi
    
    # Calculate scores
    AVG_TIME="N/A"
    if [ "$OVERVIEW_SUCCESS" = true ] && [ "$REC_SUCCESS" = true ]; then
        AVG_TIME=$(echo "scale=2; ($OVERVIEW_TIME + $REC_TIME) / 2" | bc)
    fi
    
    # Quality score based on results
    QUALITY_SCORE=0
    if [ "$OVERVIEW_SUCCESS" = true ] && [ "$OVERVIEW_LEN" -gt 100 ]; then
        QUALITY_SCORE=$((QUALITY_SCORE + 3))
    fi
    if [ "$REC_SUCCESS" = true ] && [ "$REC_COUNT" -gt 0 ]; then
        QUALITY_SCORE=$((QUALITY_SCORE + 3))
    fi
    if [ "$OVERVIEW_SUCCESS" = true ] && [ "$REC_SUCCESS" = true ]; then
        QUALITY_SCORE=$((QUALITY_SCORE + 2))
    fi
    if [ "$AVG_TIME" != "N/A" ] && [ "$(echo "$AVG_TIME < 60" | bc)" -eq 1 ]; then
        QUALITY_SCORE=$((QUALITY_SCORE + 2))
    fi
    
    echo "    Score: $QUALITY_SCORE/10"
    echo ""
    
    # Return results
    echo "$MODEL|$OVERVIEW_SUCCESS|$OVERVIEW_TIME|$OVERVIEW_LEN|$REC_SUCCESS|$REC_TIME|$REC_COUNT|$AVG_TIME|$QUALITY_SCORE"
}

# Test all models
echo "[3/5] Testing all models..."
echo "This will take 5-10 minutes per model..."
echo ""

RESULTS=""
for MODEL in $MODELS; do
    echo "----------------------------------------"
    echo "Testing: $MODEL"
    echo "----------------------------------------"
    RESULT=$(test_model "$MODEL" "$PROJECT_ID")
    RESULTS="${RESULTS}${RESULT}\n"
    sleep 5
done

# Parse results and find best
echo "[4/5] Analyzing results..."
echo ""

BEST_MODEL=""
BEST_SCORE=0
BEST_TIME=999999

while IFS='|' read -r MODEL OV_SUCCESS OV_TIME OV_LEN REC_SUCCESS REC_TIME REC_COUNT AVG_TIME QUALITY; do
    if [ "$QUALITY" -gt "$BEST_SCORE" ] || \
       ([ "$QUALITY" -eq "$BEST_SCORE" ] && [ "$AVG_TIME" != "N/A" ] && [ "$(echo "$AVG_TIME < $BEST_TIME" | bc)" -eq 1 ]); then
        BEST_MODEL="$MODEL"
        BEST_SCORE=$QUALITY
        if [ "$AVG_TIME" != "N/A" ]; then
            BEST_TIME=$AVG_TIME
        fi
    fi
done < <(echo -e "$RESULTS")

# Save results to JSON
python3 << EOF > "$RESULTS_FILE"
import json
import sys

results = []
for line in """$RESULTS""".strip().split('\n'):
    if not line:
        continue
    parts = line.split('|')
    if len(parts) >= 9:
        results.append({
            "model": parts[0],
            "overview_success": parts[1] == "true",
            "overview_time": parts[2],
            "overview_length": int(parts[3]) if parts[3].isdigit() else 0,
            "recommendations_success": parts[4] == "true",
            "recommendations_time": parts[5],
            "recommendations_count": int(parts[6]) if parts[6].isdigit() else 0,
            "average_time": parts[7],
            "quality_score": int(parts[8]) if parts[8].isdigit() else 0
        })

output = {
    "test_time": "$(date -Iseconds)",
    "project_id": "$PROJECT_ID",
    "models_tested": [m.split('|')[0] for m in """$RESULTS""".strip().split('\n') if m],
    "results": results,
    "best_model": "$BEST_MODEL",
    "best_score": $BEST_SCORE
}

print(json.dumps(output, indent=2))
EOF

# Print summary
echo "[5/5] Summary"
echo "=========================================="
echo ""
printf "%-25s %-12s %-12s %-12s %-12s\n" \
    "Model" "Overview" "Rec" "Avg Time" "Score"
echo "----------------------------------------------------------------------------"

while IFS='|' read -r MODEL OV_SUCCESS OV_TIME OV_LEN REC_SUCCESS REC_TIME REC_COUNT AVG_TIME QUALITY; do
    OV_STATUS="✗"
    if [ "$OV_SUCCESS" = "true" ]; then
        OV_STATUS="✓ ${OV_TIME}s"
    fi
    
    REC_STATUS="✗"
    if [ "$REC_SUCCESS" = "true" ]; then
        REC_STATUS="✓ ${REC_TIME}s"
    fi
    
    printf "%-25s %-12s %-12s %-12s %-12s\n" \
        "$MODEL" "$OV_STATUS" "$REC_STATUS" "$AVG_TIME" "$QUALITY/10"
done < <(echo -e "$RESULTS")

echo ""
echo "=========================================="
echo "🏆 BEST MODEL: $BEST_MODEL"
echo "   Score: $BEST_SCORE/10"
if [ "$BEST_TIME" != "999999" ]; then
    echo "   Average Time: ${BEST_TIME}s"
fi
echo "=========================================="
echo ""

# Update to best model
if [ -n "$BEST_MODEL" ]; then
    echo "Updating backend/.env to use best model..."
    sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$BEST_MODEL|" "$BACKEND_ENV"
    echo "Restarting backend..."
    docker compose -f "$COMPOSE_FILE" restart backend > /dev/null 2>&1
    echo ""
    echo "✅ Backend updated to use: $BEST_MODEL"
    echo "   Backend is restarting..."
    echo ""
    echo "Note: Original model was: $ORIGINAL_MODEL"
    echo "      If you want to revert, update backend/.env manually"
else
    echo "⚠️  Could not determine best model. Keeping original: $ORIGINAL_MODEL"
fi

echo ""
echo "Detailed results saved to: $RESULTS_FILE"
echo ""
