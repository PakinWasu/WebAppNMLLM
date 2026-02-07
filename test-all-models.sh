#!/bin/bash
# Test all available Ollama models and recommend the best one

set -e

OLLAMA_URL="http://10.4.15.52:11434"
BACKEND_ENV="/home/nmp/Downloads/WebAppNMLLM/backend/.env"
COMPOSE_FILE="docker-compose.prod.yml"

echo "=========================================="
echo "Ollama Model Comparison Test"
echo "=========================================="
echo "Ollama Server: $OLLAMA_URL"
echo ""

# Get available models
echo "Fetching available models from Ollama server..."
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
    echo "Error: Cannot connect to Ollama server or no models found"
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

# Create results file
RESULTS_FILE="model_test_results_$(date +%Y%m%d_%H%M%S).txt"
echo "Results will be saved to: $RESULTS_FILE"
echo ""

# Test each model
for MODEL in $MODELS; do
    echo "=========================================="
    echo "Testing Model: $MODEL"
    echo "=========================================="
    
    # Update .env file
    echo "Updating backend/.env..."
    sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$MODEL|" "$BACKEND_ENV"
    
    # Restart backend
    echo "Restarting backend..."
    cd /home/nmp/Downloads/WebAppNMLLM
    docker compose -f "$COMPOSE_FILE" restart backend > /dev/null 2>&1
    
    # Wait for backend to be ready
    echo "Waiting for backend to be ready..."
    sleep 10
    
    # Check if backend is ready
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1 || \
           curl -s http://localhost:8000/docs > /dev/null 2>&1; then
            echo "Backend is ready!"
            break
        fi
        sleep 2
    done
    
    echo ""
    echo "Model $MODEL is now active."
    echo ""
    echo "Please test the model manually:"
    echo "1. Open the web UI"
    echo "2. Go to a project with devices"
    echo "3. Click 'LLM Analysis' in Network Overview section"
    echo "4. Click 'LLM Analysis' in Recommendations section"
    echo "5. Note the time and quality of results"
    echo ""
    echo "Press Enter when you've finished testing this model..."
    read -r
    
    # Ask for results
    echo ""
    echo "Enter test results for $MODEL:"
    echo -n "Overview time (seconds): "
    read OVERVIEW_TIME
    echo -n "Overview quality (1-10): "
    read OVERVIEW_QUALITY
    echo -n "Recommendations time (seconds): "
    read REC_TIME
    echo -n "Recommendations quality (1-10): "
    read REC_QUALITY
    echo -n "Notes (optional): "
    read NOTES
    
    # Calculate average
    AVG_TIME=$(echo "scale=2; ($OVERVIEW_TIME + $REC_TIME) / 2" | bc 2>/dev/null || echo "N/A")
    AVG_QUALITY=$(echo "scale=2; ($OVERVIEW_QUALITY + $REC_QUALITY) / 2" | bc 2>/dev/null || echo "N/A")
    
    # Save results
    echo "$MODEL|$OVERVIEW_TIME|$OVERVIEW_QUALITY|$REC_TIME|$REC_QUALITY|$AVG_TIME|$AVG_QUALITY|$NOTES" >> "$RESULTS_FILE"
    
    echo ""
    echo "Results saved for $MODEL"
    echo ""
done

# Restore original model
echo "Restoring original model: $ORIGINAL_MODEL"
sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$ORIGINAL_MODEL|" "$BACKEND_ENV"
docker compose -f "$COMPOSE_FILE" restart backend > /dev/null 2>&1

# Print summary
echo ""
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo ""
printf "%-25s %-12s %-12s %-12s %-12s %-12s %-12s\n" \
    "Model" "Overview(s)" "OV Quality" "Rec(s)" "Rec Quality" "Avg Time" "Avg Quality"
echo "----------------------------------------------------------------------------------------------------------------"

while IFS='|' read -r MODEL OV_TIME OV_QUAL REC_TIME REC_QUAL AVG_TIME AVG_QUAL NOTES; do
    printf "%-25s %-12s %-12s %-12s %-12s %-12s %-12s\n" \
        "$MODEL" "$OV_TIME" "$OV_QUAL" "$REC_TIME" "$REC_QUAL" "$AVG_TIME" "$AVG_QUAL"
done < "$RESULTS_FILE"

echo ""
echo "Detailed results saved to: $RESULTS_FILE"
echo ""

# Find best model (highest average quality, then fastest)
BEST_MODEL=$(while IFS='|' read -r MODEL OV_TIME OV_QUAL REC_TIME REC_QUAL AVG_TIME AVG_QUAL NOTES; do
    echo "$AVG_QUAL|$AVG_TIME|$MODEL"
done < "$RESULTS_FILE" | sort -t'|' -k1,1rn -k2,2n | head -1 | cut -d'|' -f3)

if [ -n "$BEST_MODEL" ]; then
    echo "🏆 RECOMMENDED MODEL: $BEST_MODEL"
    echo ""
    echo "To use this model, update backend/.env:"
    echo "OLLAMA_MODEL=$BEST_MODEL"
    echo ""
    echo "Then restart backend:"
    echo "docker compose -f $COMPOSE_FILE restart backend"
else
    echo "⚠️  Could not determine best model. Please review results manually."
fi
