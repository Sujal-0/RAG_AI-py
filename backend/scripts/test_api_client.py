import sys
import asyncio
import uuid
import faulthandler

faulthandler.enable()
faulthandler.dump_traceback_later(60)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi.testclient import TestClient
from app.main import app

def test_chat_api():
    print("Initializing TestClient...")
    with TestClient(app) as client:
        print("Sending chat request...")
        data = {
            "query": "What are the components of the Mobiloitte AI Platform?",
            "session_id": str(uuid.uuid4())
        }
        response = client.post("/api/v1/chat", json=data)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            res_json = response.json()
            print("\n--- Answer ---")
            print(res_json.get("answer", "").encode("utf-8", "ignore").decode("utf-8", "ignore"))
        else:
            print(f"Error: {response.text}")

if __name__ == "__main__":
    test_chat_api()
