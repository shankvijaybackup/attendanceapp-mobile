import requests
import re
from datetime import date, timedelta

BASE_URL = "http://localhost:8006"
EMP_ID = "E1009"  # Kavita Rao
TARGET_DATE = str(date.today() - timedelta(days=1)) # Yesterday

def demo_full_flow():
    print(f"=== ATOMICWORK INTEGRATION DEMO (Local: {BASE_URL}) ===")
    print(f"Target Employee: {EMP_ID}")
    print(f"Target Date: {TARGET_DATE}")
    
    # 1. Simulate: User raises ticket in Atomicwork -> Call Create Request API
    print("\n[Step 1] Creating Request via API (Simulating Atomicwork Ticket)...")
    payload = {
        "emp_id": EMP_ID,
        "request_type": "CORRECT_MARKING",
        "date_start": TARGET_DATE,
        "date_end": TARGET_DATE,
        "current_status": "ABSENT",
        "desired_status": "PRESENT",
        "reason_category": "FORGOT_ID_CARD",
        "reason_text": "Forgot ID Card, authenticating via ITSM Ticket #IN-5566"
    }
    res = requests.post(f"{BASE_URL}/attendance-requests", json=payload)
    if res.status_code != 201:
        print(f"❌ Creation Failed: {res.text}")
        return
    req_id = res.json()['id']
    print(f"✅ Request Created! ID: {req_id}")

    # 2. Simulate: Manager approves in Slack/Teams -> Atomicwork calls Approve API
    print("\n[Step 2] Manager Approves -> API Call with Note...")
    approve_payload = {
        "actor_emp_id": "M2001", 
        "action": "APPROVE",
        "comment": "Manager approved via Slack"
    }
    res = requests.post(f"{BASE_URL}/attendance-requests/{req_id}/approve", json=approve_payload)
    if res.status_code == 200:
        print("✅ Approval Successful! Database updated.")
    else:
        print(f"❌ Approval Failed: {res.text}")
        return

    # 3. Verify: Admin views Employee Profile
    print(f"\n[Step 3] Login & Fetch Admin UI Profile for {EMP_ID}...")
    
    # Login first
    session = requests.Session()
    session.post(f"{BASE_URL}/admin/login", data={"username": "admin", "password": "admin"})
    
    profile_url = f"{BASE_URL}/admin/employees/{EMP_ID}"
    res = session.get(profile_url)
    
    if res.status_code == 200:
        html = res.text
        # print(f"DEBUG: HTML Content (Start): {html[:1000]}") # Commented out for cleaner output
        
        # Searching HTML for updated record...
        
        # Split by rows to be precise
        rows = html.split("<tr>")
        target_row = None
        
        # print(f"   DEBUG: Scanning {len(rows)} rows for date '{TARGET_DATE}'...") 
        for r in rows:
            if TARGET_DATE in r:
                target_row = r
                break
        
        if target_row:
            print(f"   DEBUG: Found Row: {target_row.strip()[:150]}...")
            is_present = "PRESENT" in target_row
            is_source = "ATOMICWORK" in target_row
            
            if is_present and is_source:
                 print(f"✅ Verified in UI HTML: Found 'PRESENT' and 'ATOMICWORK' source for date {TARGET_DATE}.")
                 print(f"👉 You can view it here: {profile_url}")
            else:
                 print(f"❌ Date found but data mismatch in row: {target_row.strip()[:100]}...")
        else:
            print(f"❌ Date {TARGET_DATE} NOT found in HTML table.")
    else:
        print(f"❌ Failed to load profile page: {res.status_code}")

if __name__ == "__main__":
    try:
        demo_full_flow()
    except Exception as e:
        print(f"Error: {e}")
