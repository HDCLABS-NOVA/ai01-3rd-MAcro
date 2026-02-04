
import urllib.request
import json
import datetime
import urllib.error

url = "http://localhost:8000/api/logs"

# Minimal valid payload matching client structure
payload = {
    "metadata": {
        "flow_id": "test_flow_123",
        "performance_id": "perf_test",
        "is_completed": True,
        "completion_status": "success",
        "payment_success": True
    },
    "stages": {
        "test_stage": {
            "entry_time": str(datetime.datetime.now())
        }
    }
}

data = json.dumps(payload).encode('utf-8')
headers = {'Content-Type': 'application/json'}

print(f"Sending POST to {url}...")
try:
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    with urllib.request.urlopen(req) as response:
        resp_body = response.read().decode('utf-8')
        print(f"Status: {response.status}")
        print(f"Response: {resp_body}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}")
    print(f"Error Body: {e.read().decode('utf-8')}")
except urllib.error.URLError as e:
    print(f"Connection Error: {e.reason}")
except Exception as e:
    print(f"Unexpected Error: {e}")
