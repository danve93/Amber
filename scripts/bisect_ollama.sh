#!/bin/bash
MODEL="gemma3:27b-cloud"
URL="http://localhost:11434/api/chat"

echo "Testing model $MODEL at $URL (Chat Endpoint)"

test_size() {
    SIZE=$1
    echo "--- Testing with prompt size: $SIZE bytes ---"
    PROMPT=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9 ' | fold -w $SIZE | head -n 1)
    
    # JSON payload for chat
    # Escape quotes in prompt might be needed but for alphanumeric it's fine.
    
    # We use python to generate safe JSON to avoid bash quoting hell
    python3 -c "
import requests
import sys

prompt = '$PROMPT'
payload = {
    'model': '$MODEL',
    'messages': [{'role': 'user', 'content': 'Summarize this: ' + prompt}],
    'stream': False,
    'options': {'num_ctx': 16384}
}
try:
    res = requests.post('$URL', json=payload)
    print(f'Status: {res.status_code}')
    if res.status_code != 200:
        print(res.text[:200]) # First 200 chars of error
except Exception as e:
    print(e)
"
}

# We previously failed because requests was missing. 
# Let's check if requests is available or install it, OR just use curl.
# Since we didn't install requests, let's stick to curl.

test_size_curl() {
    SIZE=$1
    echo "--- Testing with prompt size: $SIZE bytes ---"
    PROMPT=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9 ' | fold -w $SIZE | head -n 1)
    
    # Simple JSON construction - assuming PROMPT is safe (alphanumeric)
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" -d "{\"model\": \"$MODEL\", \"messages\": [{\"role\": \"user\", \"content\": \"Summarize $PROMPT\"}], \"stream\": false, \"options\": {\"num_ctx\": 16384}}" $URL)
    
    echo "Status Code: $STATUS"
}

# Bisect
for SIZE in 4096 6144
do
    test_size_curl $SIZE
done
