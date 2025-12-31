import uvicorn
import asyncio
import httpx
import multiprocessing
import time
import os
import signal

# Import app to ensure it loads correctly
from src.api.main import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")

async def test_server():
    # Wait for server to start
    print("Waiting for server to start...")
    async with httpx.AsyncClient() as client:
        for i in range(10):
            try:
                resp = await client.get("http://127.0.0.1:8001/health")
                if resp.status_code == 200:
                    print("Server is up!")
                    break
            except Exception:
                await asyncio.sleep(1)
        else:
            print("Server failed to start.")
            return

        # Run Query
        print("\nRunning RAG Query...")
        query_payload = {
            "query": "What is Amber?",
            "options": {
                "include_trace": True
            }
        }
        
        # We need an API key as per auth middleware
        headers = {"X-API-Key": "amber-dev-key-2024"}
        
        try:
            resp = await client.post(
                "http://127.0.0.1:8001/v1/query",
                json=query_payload,
                headers=headers,
                timeout=30.0
            )
            
            if resp.status_code == 200:
                data = resp.json()
                print("\n✅ Query Successful!")
                print(f"Answer: {data['answer']}")
                print(f"Sources: {len(data['sources'])}")
                for s in data['sources']:
                    print(f" - [{s['score']:.2f}] {s['text'][:50]}...")
                
                print("\nTrace:")
                for step in data.get('trace', []):
                    print(f" - {step['step']}: {step['duration_ms']:.2f}ms")
            else:
                print(f"\n❌ Query Failed: {resp.status_code}")
                print(resp.text)
                
        except Exception as e:
            print(f"\n❌ Request failed: {e}")

def main():
    # Start server in separate process
    p = multiprocessing.Process(target=run_server)
    p.start()
    
    try:
        asyncio.run(test_server())
    finally:
        print("Stopping server...")
        os.kill(p.pid, signal.SIGTERM)
        p.join()

if __name__ == "__main__":
    main()
