import requests
import json

# Target endpoint for mathematical reasoning tool
endpoint = "http://43.159.144.130:8079/tools/wolframalpha"

# Prepare request headers
req_headers = {
    "Content-Type": "application/json"
}

# Define the task payload
payload = {
    "query": "5+6"
}

# Execute POST request
try:
    result = requests.post(endpoint, headers=req_headers, data=json.dumps(payload))
    result.raise_for_status()
    print(result.json())
except Exception as err:
    print(f"Request failed: {err}")
