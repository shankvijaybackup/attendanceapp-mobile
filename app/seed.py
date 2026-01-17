import random
from datetime import date, datetime, timedelta, time
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import engine, Base, SessionLocal
from app.models import Employee, AttendanceRecord, AttendanceStatus, AttendanceChangeRequest

# Initialize DB tables
Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    
    # 1. Seed Employees
    if not db.query(Employee).first():
        print("Seeding Employees...")
        employees = [
            {"id": "E1001", "name": "Ananya Gupta", "loc": "Hyderabad", "mgr": "M2001", "email": "ananyagupta@atombanking.onmicrosoft.com", "device": "OnePlus Pad"},
            {"id": "E1002", "name": "Rahul Sharma", "loc": "Bangalore", "mgr": "M2001"},
            {"id": "E1003", "name": "Priya Patel", "loc": "Mumbai", "mgr": "M2001"},
            {"id": "E1004", "name": "Amit Kumar", "loc": "Delhi", "mgr": "M2002"},
            {"id": "E1005", "name": "Sneha Reddy", "loc": "Hyderabad", "mgr": "M2001"},
            {"id": "E1006", "name": "Vikram Singh", "loc": "Pune", "mgr": "M2002"},
            {"id": "E1007", "name": "Neha Gupta", "loc": "Gurgaon", "mgr": "M2003"},
            {"id": "E1008", "name": "Rohan Das", "loc": "Kolkata", "mgr": "M2003"},
            {"id": "E1009", "name": "Kavita Rao", "loc": "Chennai", "mgr": "M2001"},
            {"id": "E1010", "name": "Arjun Nair", "loc": "Kochi", "mgr": "M2002"},
            {"id": "E1011", "name": "Meera Joshi", "loc": "Ahmedabad", "mgr": "M2003"},
            {"id": "E1012", "name": "Siddharth Malhotra", "loc": "Hyderabad", "mgr": "M2001"},
            {"id": "E1013", "name": "Ishaan Verma", "loc": "Bangalore", "mgr": "M2002"},
            {"id": "E1014", "name": "Zoya Khan", "loc": "Mumbai", "mgr": "M2003"},
            {"id": "E1015", "name": "Aditya Roy", "loc": "Delhi", "mgr": "M2001"},
            {"id": "E1016", "name": "Nisha Agarwal", "loc": "Jaipur", "mgr": "M2002"},
            {"id": "E1017", "name": "Varun Dhawan", "loc": "Indore", "mgr": "M2003"},
            {"id": "E1018", "name": "Pooja Hegde", "loc": "Hyderabad", "mgr": "M2001"},
            {"id": "E1019", "name": "Karan Johar", "loc": "Mumbai", "mgr": "M2002"},
            {"id": "E1020", "name": "Ranbir Kapoor", "loc": "Mumbai", "mgr": "M2003"},
            {"id": "M2001", "name": "Vivek Sharma", "loc": "Hyderabad", "mgr": None},
            {"id": "M2002", "name": "Sanjay Dutt", "loc": "Mumbai", "mgr": None},
            {"id": "M2003", "name": "Shah Rukh Khan", "loc": "Delhi", "mgr": None},
        ]
        
        for e in employees:
            if not db.get(Employee, e["id"]):
                # Default email generation for others
                email = e.get("email", f"{e['name'].split()[0].lower()}@drreddys.com")
                device = e.get("device", "Samsung Galaxy S23") # Default fleet device
                
                db.add(Employee(
                    emp_id=e["id"], 
                    name=e["name"], 
                    location=e["loc"], 
                    cost_center="CC_FIELD", 
                    manager_emp_id=e["mgr"],
                    email=email,
                    device=device
                ))
        db.commit()

        # 2. History for Ananya (E1001) - Last 30 days
        print("Seeding Ananya's History...")
        ananya_recs = []
        sources = ["BIOMETRIC_GATE_1", "TEAMS_APP", "WIFI_LOGIN_FL3", "CARD_INT_05"]
        today = date.today()
        
        for i in range(30):
            d = today - timedelta(days=i)
            # Skip weekends
            if d.weekday() >= 5: 
                continue
                
            status = "PRESENT"
            src = random.choice(sources)
            
            # Simulate a few leaves/absences
            if i == 1: # Yesterday could be Leave
                status = "LEAVE"
                src = "HRMS_PORTAL"
            elif i == 14:
                status = "ABSENT"
                src = "SYSTEM_AUTO"
            elif i == 0:
                # Today: Make Ananya NOT CHECKED IN initially
                continue
                
            ananya_recs.append(AttendanceRecord(
                emp_id="E1001",
                day=d,
                status=status,
                source_system=src,
                last_updated_at=datetime.combine(d, time(9, random.randint(0, 30)))
            ))

        db.add_all(ananya_recs)
        
        # 3. Today's Data for everyone else (Random)
        print("Seeding others...")
        for e in employees:
            if e["id"] == "E1001": continue
            
            if random.random() > 0.2: # 80% Present
                db.add(AttendanceRecord(
                    emp_id=e["id"],
                    day=today,
                    status="PRESENT",
                    source_system="BIOMETRIC_GATE_MAIN",
                    last_updated_at=datetime.now()
                ))

        db.commit()
        print("Seed complete")
    else:
        print("Data already exists.")

if __name__ == "__main__":
    seed()
