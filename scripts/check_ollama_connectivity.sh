#!/bin/bash
echo "--- Checking Models on Ollama Host ---"
OLLAMA_HOST=$(grep OLLAMA_BASE_URL /root/amber2/.env | cut -d'=' -f2 | sed 's|/v1||')
echo "URL from .env: $OLLAMA_HOST"

# Try curl from host first to see what's there
curl -s "$OLLAMA_HOST/api/tags" | jq .

echo "\n--- Checking Connectivity from Worker Container ---"
CONTAINER=$(docker ps --format "{{.Names}}" | grep worker | head -n 1)
if [ -n "$CONTAINER" ]; then
    echo "Container: $CONTAINER"
    docker exec $CONTAINER curl -s --connect-timeout 5 "$OLLAMA_HOST/api/tags" > /tmp/worker_curl_test.json
    if [ -s /tmp/worker_curl_test.json ]; then
        echo "Success! Models visible from worker:"
        cat /tmp/worker_curl_test.json | jq .
    else
        echo "Failed to connect to Ollama from worker!"
    fi
else
    echo "Worker container not found!"
fi
