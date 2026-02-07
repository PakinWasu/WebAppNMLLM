#!/bin/bash
# Check status of model testing

echo "Checking model test status..."
echo ""

# Check if test is running
if pgrep -f "auto-test-and-select.sh" > /dev/null; then
    echo "✅ Test is still running"
    echo ""
    echo "Recent progress:"
    tail -20 model_test_background.log 2>/dev/null || echo "No log file found"
else
    echo "ℹ️  Test is not running"
    echo ""
fi

# Check for results
RESULTS=$(ls -t model_test_results_*.json 2>/dev/null | head -1)
if [ -n "$RESULTS" ]; then
    echo ""
    echo "📊 Results found: $RESULTS"
    echo ""
    echo "Summary:"
    cat "$RESULTS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"Models tested: {len(data.get('results', []))}\")
    print(f\"Best model: {data.get('best_model', 'N/A')}\")
    print(f\"Best score: {data.get('best_score', 'N/A')}/10\")
    print()
    print('Results:')
    for r in data.get('results', []):
        model = r.get('model', 'N/A')
        score = r.get('score', 0)
        ov = r.get('overview', {})
        rec = r.get('recommendations', {})
        ov_status = '✓' if ov.get('success') else '✗'
        rec_status = '✓' if rec.get('success') else '✗'
        print(f\"  {model}: Score {score}/10 (Overview: {ov_status}, Rec: {rec_status})\")
except Exception as e:
    print(f'Error parsing results: {e}')
" 2>/dev/null || echo "Could not parse results"
else
    echo ""
    echo "⚠️  No results file found yet"
fi

echo ""
echo "Current model in backend/.env:"
grep "^OLLAMA_MODEL=" backend/.env 2>/dev/null || echo "Not found"
