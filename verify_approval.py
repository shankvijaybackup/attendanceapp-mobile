import requests
from app.db import SessionLocal
from app.models import AttendanceRecord, AttendanceChangeRequest, RequestStatus
from datetime import date, datetime

BASE_URL = "http://localhost:8006"
EMP_ID = "E1001"
TARGET_DATE = str(date.today())

def verify_approval_flow():
    print("=== TEST START: Approval Flow & Real DB Update ===")

    # 1. Create a Request (Correction: ABSENT -> PRESENT)
    print("\n1. Creating Correction Request...")
    payload = {
        "emp_id": EMP_ID,
        "request_type": "CORRECT_MARKING",
        "date_start": TARGET_DATE,
        "date_end": TARGET_DATE,
        "current_status": "ABSENT",
        "desired_status": "PRESENT",
        "reason_category": "FORGOT_CHECKIN",
        "reason_text": "Forgot to check in, verifying Approval Flow"
    }
    res = requests.post(f"{BASE_URL}/attendance-requests", json=payload)
    if res.status_code != 201:
        print(f"❌ Failed to create request: {res.text}")
        return
    
    req_id = res.json()['id']
    print(f"✅ Request Created (ID: {req_id})")

    # 2. Approve the Request (As Manager/Admin)
    print("\n2. Approving Request...")
    # Admin session cookie simulation if needed, or just hit the endpoint 
    # The endpoint checks for 'approver_emp_id' matching payload actor, 
    # but for simple testing we might need to bypass or provide correct actor.
    # In 'create_request', approver is set to emp.manager_emp_id.
    # E1001 manager is M2001.
    
    approve_payload = {
        "actor_emp_id": "M2001",
        "action": "APPROVE",
        "comment": "Approved via Atomicwork ITSM (Ticket #IN-9988)"
    }
    
    res = requests.post(f"{BASE_URL}/attendance-requests/{req_id}/approve", json=approve_payload)
    if res.status_code == 200:
        print("✅ Atomicwork Approval API Called Successfully")
    else:
        print(f"❌ Failed to approve: {res.text}")
        return

    # 3. Verify DB Update (Direct Check)
    print("\n3. Verifying Database Update & Audit...")
    db = SessionLocal()
    try:
        # Check Request Status
        req = db.get(AttendanceChangeRequest, req_id)
        print(f"   Request Status: {req.status} (Expected: APPLIED)")

        # Check Audit Log for Atomicwork Note
        latest_audit = req.audit_events[-1]
        print(f"   Latest Audit Note: {latest_audit.comment}")
        
        # Check Attendance Record
        rec = db.query(AttendanceRecord).filter(
            AttendanceRecord.emp_id == EMP_ID,
            AttendanceRecord.day == date.today()
        ).first()

        if rec:
            print(f"   Record Status: {rec.status} (Expected: PRESENT)")
            print(f"   Source System: {rec.source_system} (Expected: ATOMICWORK)")
            
            if rec.status == "PRESENT" and rec.source_system == "ATOMICWORK":
                print("\n✅ SUCCESS: Integrated Authorization Flow Confirmed!")
            else:
                print("\n❌ FAILURE: Record data mismatch.")
        else:
            print("\n❌ FAILURE: Attendance Record not found.")
            
    finally:
        db.close()

if __name__ == "__main__":
    try:
        verify_approval_flow()
    except Exception as e:
        print(f"Error: {e}")
