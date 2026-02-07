#!/bin/bash
# Wait for model testing to complete and show results

echo "Waiting for model testing to complete..."
echo "This may take 15-30 minutes..."
echo ""

# Wait for process to finish
while pgrep -f "auto-test-and-select.sh" > /dev/null; do
    echo -n "."
    sleep 30
done

echo ""
echo ""
echo "=========================================="
echo "Testing Complete!"
echo "=========================================="
echo ""

# Show results
RESULTS=$(ls -t model_test_results_*.json 2>/dev/null | head -1)
if [ -n "$RESULTS" ]; then
    echo "📊 Results:"
    echo ""
    cat "$RESULTS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"Test Time: {data.get('test_time', 'N/A')}\")
    print(f\"Models Tested: {', '.join(data.get('models_tested', []))}\")
    print()
    print('=' * 80)
    print('RESULTS SUMMARY')
    print('=' * 80)
    print()
    print(f\"{'Model':<25} {'Overview':<15} {'Rec':<15} {'Avg Time':<12} {'Score':<10}\")
    print('-' * 80)
    
    for r in data.get('results', []):
        model = r.get('model', 'N/A')
        score = r.get('score', 0)
        ov = r.get('overview', {})
        rec = r.get('recommendations', {})
        
        ov_status = '✗'
        ov_time = 'N/A'
        if ov.get('success'):
            ov_status = '✓'
            ov_time = f\"{ov.get('elapsed_time', 0):.1f}s\"
        
        rec_status = '✗'
        rec_time = 'N/A'
        if rec.get('success'):
            rec_status = '✓'
            rec_time = f\"{rec.get('elapsed_time', 0):.1f}s\"
        
        avg_time = 'N/A'
        if ov.get('success') and rec.get('success'):
            avg_time = f\"{(ov.get('elapsed_time', 0) + rec.get('elapsed_time', 0)) / 2:.1f}s\"
        
        print(f\"{model:<25} {ov_status} {ov_time:<12} {rec_status} {rec_time:<12} {avg_time:<12} {score}/10\")
    
    print()
    print('=' * 80)
    best_model = data.get('best_model', 'N/A')
    best_score = data.get('best_score', 'N/A')
    print(f\"🏆 BEST MODEL: {best_model}\")
    print(f\"   Score: {best_score}/10\")
    print('=' * 80)
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
" 2>/dev/null || cat "$RESULTS"
    
    echo ""
    echo "Current model in backend/.env:"
    grep "^OLLAMA_MODEL=" backend/.env 2>/dev/null || echo "Not found"
else
    echo "⚠️  No results file found"
    echo ""
    echo "Check logs:"
    tail -50 model_test_background.log 2>/dev/null || echo "No log file"
fi
