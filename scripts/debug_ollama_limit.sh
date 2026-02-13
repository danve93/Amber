#!/bin/bash
MODEL="gemma3:27b-cloud"
URL="http://localhost:11434/api/generate"

echo "Testing model $MODEL at $URL"

# Generate a large prompt using dd from /dev/urandom and tr
# 2048 chars ~ 512 tokens
# 8192 chars ~ 2048 tokens
# 16000 chars ~ 4000 tokens
# 32000 chars ~ 8000 tokens
# 128000 chars ~ 32000 tokens

for SIZE in 2048 8192 16384 32768 65536 131072
do
    echo "--- Testing with prompt size: $SIZE bytes ---"
    PROMPT=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9 ' | fold -w $SIZE | head -n 1)
    
    # Use curl with -w to get status code
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" -d "{\"model\": \"$MODEL\", \"prompt\": \"Summarize this text: $PROMPT\", \"stream\": false}" $URL)
    
    echo "Status Code: $STATUS"
    
    if [ "$STATUS" != "200" ]; then
        echo "Failed at size $SIZE! Response body:"
        curl -s -d "{\"model\": \"$MODEL\", \"prompt\": \"Summarize this text: $PROMPT\", \"stream\": false}" $URL
        exit 1
    fi
    echo "Success for size $SIZE"
    echo ""
done

echo "All tests completed successfully up to 128KB prompt."
