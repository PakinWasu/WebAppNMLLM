#!/bin/bash
# Test topology generation directly

echo "Testing Topology Generation..."
echo ""

# Get token
TOKEN=$(curl -s -X POST "http://10.4.15.167:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "❌ Failed to get token"
    exit 1
fi

echo "✅ Got token"
echo ""

# Test topology generation
PROJECT_ID="14d2baf4-5e75-4e5f-9fed-c42a8c1f70a2"
echo "Testing project: $PROJECT_ID"
echo ""

RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "http://10.4.15.167:8000/projects/$PROJECT_ID/topology/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')

echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Success!"
    echo "$BODY" | jq '.topology.nodes | length' | xargs -I {} echo "Nodes: {}"
    echo "$BODY" | jq '.topology.edges | length' | xargs -I {} echo "Edges: {}"
    echo "$BODY" | jq '.metrics.inference_time_ms' | xargs -I {} echo "Time: {} ms"
    echo ""
    echo "Full response:"
    echo "$BODY" | jq
else
    echo "❌ Error!"
    echo "$BODY"
fi
