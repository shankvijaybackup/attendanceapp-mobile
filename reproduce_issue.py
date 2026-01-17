import requests
import json

BASE_URL = "http://localhost:8013"
ENDPOINT = f"{BASE_URL}/api/atomicwork/sync-attendance"

payload_dict = {
    "emp_id": "E1005",
    "date": "2026-01-26",
    "status": "PRESENT",
    "reason": "WORKING ON HOLIDAY",
    "approval_note": "Approved by Manager -Vivek Sharma (M2001) - ITSER-7802"
}

# Double encode: The body becomes a string like "{\"emp_id\": ...}"
# This mimics what happens if Atomicwork or a tool sends 'Text' but claims 'application/json' 
# or wraps the JSON in quotes.
double_encoded_body = json.dumps(payload_dict) 

# Note: requests.post(json=...) does one encoding. 
# We want to send the *string* as the JSON body.
# So we effectively send: "{\"emp_id\":...}" as the *value* of the body? 
# No, usually this happens when the tool treats the whole input as a string value.

print(f"Sending double-encoded body: {double_encoded_body}")

# We send it as a raw string body, but Content-Type application/json tells FastAPI to parse it.
# If FastAPI parses it, it gets a String. But the Schema expects a Dict.
res = requests.post(
    ENDPOINT, 
    data=json.dumps(double_encoded_body), # This sends "{\"emp_id\":...}" as the JSON content
    headers={"Content-Type": "application/json"}
)

print(f"Status: {res.status_code}")
print(f"Response: {res.text}")
