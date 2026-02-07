#!/bin/bash
# Automatically test all Ollama models and select the best one

set -e

OLLAMA_URL="http://10.4.15.52:11434"
BACKEND_ENV="/home/nmp/Downloads/WebAppNMLLM/backend/.env"
COMPOSE_FILE="docker-compose.prod.yml"

echo "=========================================="
echo "Automatic Ollama Model Testing & Selection"
echo "=========================================="
echo "Ollama Server: $OLLAMA_URL"
echo "This will test all models and select the best one automatically"
echo "Estimated time: 15-30 minutes"
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

# Backup original model
ORIGINAL_MODEL=$(grep "^OLLAMA_MODEL=" "$BACKEND_ENV" | cut -d'=' -f2 || echo "deepseek-r1:7b")
echo "Current model: $ORIGINAL_MODEL"
echo ""

# Results file
RESULTS_FILE="model_test_results_$(date +%Y%m%d_%H%M%S).json"
echo "Results will be saved to: $RESULTS_FILE"
echo ""

# Test function - runs inside container
test_model_in_container() {
    local MODEL=$1
    
    docker compose -f "$COMPOSE_FILE" exec -T backend python3 << EOF
import os
import sys
import asyncio
import time
import json
from datetime import datetime

sys.path.insert(0, '/app')

# Set model
os.environ['OLLAMA_MODEL'] = '$MODEL'

from app.services.llm_service import LLMService

# Sample test data
SAMPLE_DEVICES_DATA = [
    {
        "device_id": "test-switch-01",
        "hostname": "SW-CORE-01",
        "parsed_config": {
            "device_overview": {
                "hostname": "SW-CORE-01",
                "vendor": "Cisco",
                "model": "Catalyst 9300",
                "role": "core"
            },
            "interfaces": [
                {"name": "GigabitEthernet0/1", "status": "up", "description": "Link to DIST-01"},
                {"name": "GigabitEthernet0/2", "status": "up", "description": "Link to DIST-02"}
            ],
            "vlans": [{"id": 10, "name": "VLAN10"}, {"id": 20, "name": "VLAN20"}],
            "routing": {"protocol": "OSPF", "area": 0}
        }
    },
    {
        "device_id": "test-switch-02",
        "hostname": "SW-DIST-01",
        "parsed_config": {
            "device_overview": {
                "hostname": "SW-DIST-01",
                "vendor": "Cisco",
                "model": "Catalyst 2960",
                "role": "distribution"
            },
            "interfaces": [
                {"name": "GigabitEthernet0/1", "status": "up", "description": "Link to CORE-01"},
                {"name": "GigabitEthernet0/2", "status": "down", "description": "Unused"}
            ],
            "vlans": [{"id": 10, "name": "VLAN10"}]
        }
    }
]

async def test_overview():
    llm_service = LLMService()
    llm_service.model_name = '$MODEL'
    
    start = time.time()
    try:
        result = await llm_service.analyze_project_overview(
            devices_data=SAMPLE_DEVICES_DATA,
            project_id="test-comparison"
        )
        elapsed = time.time() - start
        overview_text = result.get("overview_text", "")
        return {
            "success": True,
            "elapsed_time": elapsed,
            "overview_length": len(overview_text),
            "error": None
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "success": False,
            "elapsed_time": elapsed,
            "overview_length": 0,
            "error": str(e)
        }

async def test_recommendations():
    llm_service = LLMService()
    llm_service.model_name = '$MODEL'
    
    start = time.time()
    try:
        result = await llm_service.analyze_project_recommendations(
            devices_data=SAMPLE_DEVICES_DATA,
            project_id="test-comparison"
        )
        elapsed = time.time() - start
        recommendations = result.get("recommendations", [])
        return {
            "success": True,
            "elapsed_time": elapsed,
            "recommendations_count": len(recommendations),
            "error": None
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "success": False,
            "elapsed_time": elapsed,
            "recommendations_count": 0,
            "error": str(e)
        }

async def main():
    overview = await test_overview()
    await asyncio.sleep(2)
    recommendations = await test_recommendations()
    
    # Calculate score
    score = 0
    if overview["success"]:
        score += 3
        if overview["overview_length"] > 200:
            score += 2
        elif overview["overview_length"] > 100:
            score += 1
    
    if recommendations["success"]:
        score += 3
        if recommendations["recommendations_count"] > 3:
            score += 2
        elif recommendations["recommendations_count"] > 0:
            score += 1
    
    if overview["success"] and recommendations["success"]:
        avg_time = (overview["elapsed_time"] + recommendations["elapsed_time"]) / 2
        if avg_time < 30:
            score += 2
        elif avg_time < 60:
            score += 1
    
    score = min(score, 10)
    
    result = {
        "model": '$MODEL',
        "overview": overview,
        "recommendations": recommendations,
        "score": score
    }
    
    print(json.dumps(result))

asyncio.run(main())
EOF
}

# Test all models
echo "[2/5] Testing all models..."
echo "This will take 5-10 minutes per model..."
echo ""

RESULTS=""
for MODEL in $MODELS; do
    echo "----------------------------------------"
    echo "Testing: $MODEL"
    echo "----------------------------------------"
    
    # Update .env
    sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$MODEL|" "$BACKEND_ENV"
    
    # Restart backend
    echo "  Restarting backend..."
    cd /home/nmp/Downloads/WebAppNMLLM
    docker compose -f "$COMPOSE_FILE" restart backend > /dev/null 2>&1
    sleep 10
    
    # Test
    echo "  Running tests..."
    RESULT=$(test_model_in_container "$MODEL" 2>&1 | tail -1)
    
    if echo "$RESULT" | python3 -c "import sys, json; json.load(sys.stdin)" 2>/dev/null; then
        echo "  ✓ Test completed"
        RESULTS="${RESULTS}${RESULT}\n"
    else
        echo "  ✗ Test failed: $RESULT"
    fi
    
    echo ""
    sleep 3
done

# Parse results
echo "[3/5] Analyzing results..."
echo ""

BEST_MODEL=""
BEST_SCORE=0
BEST_TIME=999999

while IFS= read -r line; do
    if [ -z "$line" ]; then
        continue
    fi
    
    MODEL=$(echo "$line" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['model'])" 2>/dev/null)
    SCORE=$(echo "$line" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['score'])" 2>/dev/null)
    OV_TIME=$(echo "$line" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['overview']['elapsed_time'] if d['overview']['success'] else 999999)" 2>/dev/null)
    REC_TIME=$(echo "$line" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['recommendations']['elapsed_time'] if d['recommendations']['success'] else 999999)" 2>/dev/null)
    
    if [ -z "$MODEL" ] || [ -z "$SCORE" ]; then
        continue
    fi
    
    AVG_TIME=999999
    if [ "$OV_TIME" != "999999" ] && [ "$REC_TIME" != "999999" ]; then
        AVG_TIME=$(echo "scale=2; ($OV_TIME + $REC_TIME) / 2" | bc)
    fi
    
    if [ "$SCORE" -gt "$BEST_SCORE" ] || \
       ([ "$SCORE" -eq "$BEST_SCORE" ] && [ "$(echo "$AVG_TIME < $BEST_TIME" | bc)" -eq 1 ]); then
        BEST_MODEL="$MODEL"
        BEST_SCORE=$SCORE
        BEST_TIME=$AVG_TIME
    fi
done < <(echo -e "$RESULTS")

# Save results
echo -e "$RESULTS" | python3 << EOF > "$RESULTS_FILE"
import sys, json
results = []
for line in sys.stdin:
    line = line.strip()
    if line:
        try:
            results.append(json.loads(line))
        except:
            pass

output = {
    "test_time": "$(date -Iseconds)",
    "models_tested": [r.get('model') for r in results],
    "results": results,
    "best_model": "$BEST_MODEL",
    "best_score": $BEST_SCORE
}
print(json.dumps(output, indent=2))
EOF

# Print summary
echo "[4/5] Summary"
echo "=========================================="
echo ""
printf "%-25s %-15s %-15s %-12s %-10s\n" \
    "Model" "Overview" "Rec" "Avg Time" "Score"
echo "----------------------------------------------------------------------------"

echo -e "$RESULTS" | while IFS= read -r line; do
    if [ -z "$line" ]; then
        continue
    fi
    
    MODEL=$(echo "$line" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['model'])" 2>/dev/null)
    OV_SUCCESS=$(echo "$line" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['overview']['success'])" 2>/dev/null)
    OV_TIME=$(echo "$line" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"{d['overview']['elapsed_time']:.1f}\" if d['overview']['success'] else 'FAIL')" 2>/dev/null)
    REC_SUCCESS=$(echo "$line" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['recommendations']['success'])" 2>/dev/null)
    REC_TIME=$(echo "$line" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"{d['recommendations']['elapsed_time']:.1f}\" if d['recommendations']['success'] else 'FAIL')" 2>/dev/null)
    SCORE=$(echo "$line" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['score'])" 2>/dev/null)
    
    if [ -z "$MODEL" ]; then
        continue
    fi
    
    OV_STATUS="✗"
    if [ "$OV_SUCCESS" = "True" ]; then
        OV_STATUS="✓ ${OV_TIME}s"
    fi
    
    REC_STATUS="✗"
    if [ "$REC_SUCCESS" = "True" ]; then
        REC_STATUS="✓ ${REC_TIME}s"
    fi
    
    AVG_TIME="N/A"
    if [ "$OV_SUCCESS" = "True" ] && [ "$REC_SUCCESS" = "True" ]; then
        AVG_TIME=$(echo "scale=1; ($OV_TIME + $REC_TIME) / 2" | bc)
        AVG_TIME="${AVG_TIME}s"
    fi
    
    printf "%-25s %-15s %-15s %-12s %-10s\n" \
        "$MODEL" "$OV_STATUS" "$REC_STATUS" "$AVG_TIME" "$SCORE/10"
done

echo ""
echo "=========================================="
if [ -n "$BEST_MODEL" ]; then
    echo "🏆 BEST MODEL: $BEST_MODEL"
    echo "   Score: $BEST_SCORE/10"
    if [ "$BEST_TIME" != "999999" ]; then
        echo "   Average Time: ${BEST_TIME}s"
    fi
else
    echo "⚠️  Could not determine best model"
fi
echo "=========================================="
echo ""

# Update to best model
if [ -n "$BEST_MODEL" ]; then
    echo "[5/5] Updating to best model..."
    sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$BEST_MODEL|" "$BACKEND_ENV"
    echo "Restarting backend..."
    docker compose -f "$COMPOSE_FILE" restart backend > /dev/null 2>&1
    echo ""
    echo "✅ Backend updated to use: $BEST_MODEL"
    echo "   Backend is restarting..."
    echo ""
    echo "Note: Original model was: $ORIGINAL_MODEL"
else
    echo "[5/5] Keeping original model: $ORIGINAL_MODEL"
fi

echo ""
echo "Detailed results saved to: $RESULTS_FILE"
echo ""
