import requests
from datetime import date

BASE_URL = "http://localhost:8007"

def verify_sync():
    print(f"Testing Sync Endpoint at: {BASE_URL}")
    
    url = f"{BASE_URL}/api/atomicwork/sync-attendance"
    payload = {
        "emp_id": "E1009",
        "date": str(date.today()),
        "status": "PRESENT",
        "reason": "Sync Test Local",
        "approval_note": "Local Sync Test"
    }
    
    try:
        res = requests.post(url, json=payload)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
        
        if res.status_code == 200:
            print("✅ Endpoint is working locally!")
        else:
            print("❌ Endpoint returned error locally.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    verify_sync()
