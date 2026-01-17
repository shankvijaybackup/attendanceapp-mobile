
import requests
import json
from datetime import date, timedelta

BASE_URL = "http://localhost:8005"
EMP_ID = "E1001"

def verify_audit():
    print("1. Creating Leave Request with Reason...")
    payload = {
        "emp_id": EMP_ID,
        "request_type": "HOLIDAY_EXCEPTION",
        "date_start": str(date.today()),
        "date_end": str(date.today()),
        "current_status": "ABSENT",
        "desired_status": "PRESENT",
        "reason_category": "HOLIDAY_WORK",
        "reason_text": "Urgent deployment for Dr. Reddy's Audit Logic"
    }
    
    res = requests.post(f"{BASE_URL}/attendance-requests", json=payload)
    if res.status_code != 201:
        print(f"FAILED to create request: {res.text}")
        return
    
    req_data = res.json()
    req_id = req_data['id']
    print(f"Request Created: ID {req_id}")
    
    # Verify Reason Text in Response
    if req_data.get('reason_text') == payload['reason_text']:
        print("✅ Reason Text verified in Creation Response")
    else:
        print(f"❌ Reason Text Mismatch: {req_data.get('reason_text')}")

    print("\n2. Fetching Audit Logs...")
    res = requests.get(f"{BASE_URL}/attendance-requests/{req_id}/audit")
    if res.status_code != 200:
        print(f"FAILED to fetch audit: {res.text}")
        return

    audit_logs = res.json()
    print(json.dumps(audit_logs, indent=2))
    
    # Verify Created Event
    created_event = next((a for a in audit_logs if a['action'] == 'REQUEST_CREATED'), None)
    if created_event and created_event['comment'] == payload['reason_text']:
         print("✅ REQUEST_CREATED event found with correct comment (Reason)")
    else:
         print("❌ REQUEST_CREATED event missing or comment mismatch")

if __name__ == "__main__":
    try:
        verify_audit()
    except Exception as e:
        print(f"Error: {e}")
