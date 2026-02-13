#!/bin/bash
echo "--- 1. Checking Ollama on Host (Localhost) ---"
# Check if Ollama is running on localhost
if curl -s --connect-timeout 2 "http://localhost:11434/api/tags" > /dev/null; then
    echo "SUCCESS: Ollama is running on localhost:11434"
    echo "Models available:"
    curl -s "http://localhost:11434/api/tags" | jq -r '.models[].name'
else
    echo "FAILURE: Ollama is NOT reachable on localhost:11434"
fi

echo "\n--- 2. Checking IP from .env ---"
OLLAMA_HOST=$(grep OLLAMA_BASE_URL /root/amber2/.env | cut -d'=' -f2 | sed 's|/v1||' | tr -d '"' | tr -d "'")
echo "Configured URL: $OLLAMA_HOST"

if curl -s --connect-timeout 2 "$OLLAMA_HOST/api/tags" > /dev/null; then
    echo "SUCCESS: Ollama is reachable at configured URL"
else
    echo "FAILURE: Ollama is NOT reachable at configured URL"
fi

echo "\n--- 3. Checking Connectivity from Worker Container ---"
CONTAINER=$(docker ps --format "{{.Names}}" | grep worker | head -n 1)
if [ -n "$CONTAINER" ]; then
    echo "Container: $CONTAINER"
    # Try configured URL
    echo "Trying configured URL from worker..."
    docker exec $CONTAINER curl -s --connect-timeout 2 "$OLLAMA_HOST/api/tags" > /tmp/worker_test_config.json
    if [ -s /tmp/worker_test_config.json ]; then
        echo "SUCCESS: Worker can connect using configured URL."
    else
        echo "FAILURE: Worker cannot connect using configured URL."
    fi
    
    # Try host.docker.internal
    echo "Trying host.docker.internal from worker..."
    docker exec $CONTAINER curl -s --connect-timeout 2 "http://host.docker.internal:11434/api/tags" > /tmp/worker_test_internal.json
    if [ -s /tmp/worker_test_internal.json ]; then
        echo "SUCCESS: Worker can connect using host.docker.internal."
    else
        echo "FAILURE: Worker cannot connect using host.docker.internal."
    fi
else
    echo "Worker container not found!"
fi
