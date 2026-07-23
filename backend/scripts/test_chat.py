import sys
import requests
import json
import uuid

# Force stdout to UTF-8 to prevent charmap errors on Windows
sys.stdout.reconfigure(encoding='utf-8')

url = "http://127.0.0.1:8000/api/v1/chat"
headers = {"Content-Type": "application/json"}
data = {
    "query": "What are the components of the Mobiloitte AI Platform?",
    "session_id": str(uuid.uuid4())
}

import time

for attempt in range(10):
    try:
        response = requests.post(url, headers=headers, json=data)
        break
    except requests.exceptions.ConnectionError:
        print("Waiting for server to start...")
        time.sleep(2)
else:
    print("Failed to connect after retries.")
    exit(1)

if response.status_code == 200:
    res_json = response.json()
    print("\n--- Answer ---")
    print(res_json.get("answer", ""))
    print("\n--- Intent ---")
    print(res_json.get("intent"))
    print("\n--- Citations ---")
    citations = res_json.get("citations", [])
    for idx, c in enumerate(citations):
        print(f"[{idx+1}] {c.get('documentName')} (Similarity: {c.get('similarityScore', 0):.2f})")
    
    # Check debug info for retrieval performance
    metadata = res_json.get("metadata", {})
    if "debug" in metadata:
        print("\n--- Debug Info ---")
        debug_info = metadata["debug"]
        print(f"Strategy: {debug_info.get('strategy')}")
        print(f"Retrieval Count: {debug_info.get('retrieval_count')}")
else:
    print(f"Error {response.status_code}: {response.text}")
