from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, List
import os

from pydantic import BaseModel

from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from .db import SessionLocal
from .models import (
    Employee,
    AttendanceRecord,
    AttendanceChangeRequest,
    AuditEvent,
    RequestStatus,
)
from .schemas import (
    EmployeeOut,
    AttendanceRecordOut,
    RequestCreateIn,
    RequestOut,
    RequestActionIn,
    AuditEventOut,
    AtomicworkSyncIn,
)
from .seed import seed

app = FastAPI(title="Attendance Service (SAP Mock)", version="0.1.0")

# Optional admin UI assets
# Optional admin UI assets
base_dir = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(base_dir, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(base_dir, "templates"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/version")
def api_version():
    return {
        "version": "1.2.0",
        "features": ["atomicwork_sync", "audit_logs", "employee_profile_ui"],
        "last_updated": datetime.utcnow().isoformat()
    }


@app.post("/api/atomicwork/sync-attendance", status_code=200)
def atomicwork_sync(payload: AtomicworkSyncIn, db: Session = Depends(get_db)):
    """
    Directly apply attendance changes from Atomicwork.
    No approval flow needed inside this app; it assumes the request is already approved.
    """
    # 1. Create Request Record (for audit history)
    req = AttendanceChangeRequest(
        emp_id=payload.emp_id,
        request_type="ATOMICWORK_SYNC",
        date_start=payload.date,
        date_end=payload.date,
        current_status="UNKNOWN", # We don't verify current status in sync
        desired_status=payload.status,
        reason_category="ATOMICWORK",
        reason_text=payload.reason,
        approver_emp_id="ATOMICWORK_SYSTEM",
        status=RequestStatus.APPLIED.value,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(req)
    db.flush()

    # 2. Add Audit Log
    _add_audit(db, req.id, actor_emp_id="ATOMICWORK", action="SYNC_APPLIED", comment=payload.approval_note)

    # 3. Apply Change to Attendance Table
    rec = db.execute(
        select(AttendanceRecord).where(and_(AttendanceRecord.emp_id == payload.emp_id, AttendanceRecord.day == payload.date))
    ).scalars().first()

    if rec:
        rec.status = payload.status
        rec.last_updated_by = "ATOMICWORK"
        rec.last_updated_at = datetime.utcnow()
        rec.source_system = "ATOMICWORK"
    else:
        db.add(
            AttendanceRecord(
                emp_id=payload.emp_id,
                day=payload.date,
                status=payload.status,
                source_system="ATOMICWORK",
                last_updated_by="ATOMICWORK",
                last_updated_at=datetime.utcnow(),
            )
        )
    
    db.commit()
    return {"status": "success", "message": "Synced successfully", "request_id": req.id}




import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("startup")
def _startup():
    try:
        # Create DB + seed demo data if empty.
        seed()
        logger.info("Database seeding completed.")
    except Exception as e:
        logger.error(f"Error during database seeding: {e}", exc_info=True)
        # We catch the error so the app can still start



# -----------------------------
# Helpers
# -----------------------------

def _add_audit(db: Session, request_id: int, actor_emp_id: Optional[str], action: str, comment: Optional[str] = None):
    db.add(AuditEvent(request_id=request_id, actor_emp_id=actor_emp_id, action=action, comment=comment))


def _daterange(start: date, end: date):
    if end < start:
        raise HTTPException(status_code=400, detail="date_end must be >= date_start")
    cur = start
    while cur <= end:
        yield cur
        cur = cur + timedelta(days=1)


def _apply_change(db: Session, req: AttendanceChangeRequest, actor_emp_id: str):
    """Apply the request into AttendanceRecord rows (mock 'SAP update')."""
    # For unlock-only requests without desired_status, we only log an audit event.
    if not req.desired_status:
        return

    for d in _daterange(req.date_start, req.date_end):
        rec = db.execute(
            select(AttendanceRecord).where(and_(AttendanceRecord.emp_id == req.emp_id, AttendanceRecord.day == d))
        ).scalars().first()

        if rec:
            rec.status = req.desired_status
            rec.last_updated_by = actor_emp_id
            rec.last_updated_at = datetime.utcnow()
            rec.source_system = "ATOMICWORK"
        else:
            db.add(
                AttendanceRecord(
                    emp_id=req.emp_id,
                    day=d,
                    status=req.desired_status,
                    source_system="ATOMICWORK",
                    last_updated_by=actor_emp_id,
                    last_updated_at=datetime.utcnow(),
                )
            )


# -----------------------------
# API
# -----------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return RedirectResponse(url="/mobile")


@app.get("/employees/{emp_id}", response_model=EmployeeOut)
def get_employee(emp_id: str, db: Session = Depends(get_db)):
    emp = db.get(Employee, emp_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


@app.get("/employees/{emp_id}/manager", response_model=EmployeeOut)
def get_manager(emp_id: str, db: Session = Depends(get_db)):
    emp = db.get(Employee, emp_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    if not emp.manager_emp_id:
        raise HTTPException(status_code=404, detail="Manager not configured for employee")
    mgr = db.get(Employee, emp.manager_emp_id)
    if not mgr:
        raise HTTPException(status_code=404, detail="Manager record not found")
    return mgr


@app.get("/attendance", response_model=List[AttendanceRecordOut])
def list_attendance(emp_id: str, start: date, end: date, db: Session = Depends(get_db)):
    rows = db.execute(
        select(AttendanceRecord).where(
            and_(AttendanceRecord.emp_id == emp_id, AttendanceRecord.day >= start, AttendanceRecord.day <= end)
        ).order_by(AttendanceRecord.day.asc())
    ).scalars().all()
    return rows


@app.post("/attendance-requests", response_model=RequestOut, status_code=201)
def create_request(payload: RequestCreateIn, db: Session = Depends(get_db)):
    emp = db.get(Employee, payload.emp_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    approver_emp_id = emp.manager_emp_id

    req = AttendanceChangeRequest(
        emp_id=payload.emp_id,
        request_type=payload.request_type,
        date_start=payload.date_start,
        date_end=payload.date_end,
        current_status=payload.current_status,
        desired_status=payload.desired_status,
        reason_category=(payload.reason_category or "OTHER"),
        reason_text=payload.reason_text,
        approver_emp_id=approver_emp_id,
        status=RequestStatus.PENDING_APPROVAL.value,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(req)
    db.flush()  # assign id

    _add_audit(db, req.id, actor_emp_id=payload.emp_id, action="REQUEST_CREATED", comment=payload.reason_text)
    db.commit()
    db.refresh(req)
    return req


@app.get("/attendance-requests/{request_id}", response_model=RequestOut)
def get_request(request_id: int, db: Session = Depends(get_db)):
    req = db.get(AttendanceChangeRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


@app.get("/attendance-requests/{request_id}/audit", response_model=List[AuditEventOut])
def get_request_audit(request_id: int, db: Session = Depends(get_db)):
    req = db.get(AttendanceChangeRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req.audit_events


@app.post("/attendance-requests/{request_id}/approve", response_model=RequestOut)
def approve_request(request_id: int, payload: RequestActionIn, db: Session = Depends(get_db)):
    req = db.get(AttendanceChangeRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.status not in [RequestStatus.PENDING_APPROVAL.value, RequestStatus.DRAFT.value]:
        raise HTTPException(status_code=409, detail=f"Cannot approve request in status {req.status}")

    # Simple authorization: actor must be configured approver
    if req.approver_emp_id and payload.actor_emp_id != req.approver_emp_id:
        raise HTTPException(status_code=403, detail="Only the configured approver can approve")

    req.status = RequestStatus.APPROVED.value
    req.updated_at = datetime.utcnow()
    _add_audit(db, req.id, actor_emp_id=payload.actor_emp_id, action="APPROVED", comment=payload.comment)

    try:
        _apply_change(db, req, actor_emp_id=payload.actor_emp_id)
        req.status = RequestStatus.APPLIED.value
        req.updated_at = datetime.utcnow()
        _add_audit(db, req.id, actor_emp_id=payload.actor_emp_id, action="APPLIED", comment="Applied via Atomicwork")
    except Exception as e:
        req.status = RequestStatus.FAILED.value
        req.updated_at = datetime.utcnow()
        _add_audit(db, req.id, actor_emp_id=payload.actor_emp_id, action="FAILED", comment=str(e))
        db.commit()
        db.refresh(req)
        raise

    db.commit()
    db.refresh(req)
    return req


@app.post("/attendance-requests/{request_id}/reject", response_model=RequestOut)
def reject_request(request_id: int, payload: RequestActionIn, db: Session = Depends(get_db)):
    req = db.get(AttendanceChangeRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.status not in [RequestStatus.PENDING_APPROVAL.value, RequestStatus.DRAFT.value]:
        raise HTTPException(status_code=409, detail=f"Cannot reject request in status {req.status}")

    if req.approver_emp_id and payload.actor_emp_id != req.approver_emp_id:
        raise HTTPException(status_code=403, detail="Only the configured approver can reject")

    req.status = RequestStatus.REJECTED.value
    req.updated_at = datetime.utcnow()
    _add_audit(db, req.id, actor_emp_id=payload.actor_emp_id, action="REJECTED", comment=payload.comment)

    db.commit()
    db.refresh(req)
    return req


# -----------------------------
# Admin UI (optional)
# -----------------------------

# -----------------------------
# Simulation Logic
# -----------------------------
SIMULATION_STATE = "NORMAL"  # NORMAL, HOLIDAY, LOCKOUT

class SimulationIn(BaseModel):
    state: str

@app.get("/simulate", response_class=HTMLResponse)
def simulation_ui(request: Request):
    return templates.TemplateResponse("simulation.html", {"request": request})

@app.get("/api/simulate")
def get_simulation_state():
    return {"state": SIMULATION_STATE}

@app.post("/api/simulate")
def set_simulation_state(payload: SimulationIn):
    global SIMULATION_STATE
    if payload.state not in ["NORMAL", "HOLIDAY", "LOCKOUT", "UNLOCK_RESTRICTION"]:
        raise HTTPException(status_code=400, detail="Invalid state")
    SIMULATION_STATE = payload.state
    return {"state": SIMULATION_STATE}

# 2026 Indian Holidays (Fixed Set)
INDIAN_HOLIDAYS = {
    (1, 26),  # Republic Day
    (5, 1),   # Labor Day / Maharashtra Day
    (8, 15),  # Independence Day
    (10, 2),  # Gandhi Jayanti
    (12, 25), # Christmas
    (11, 8),  # Diwali (Approx for demo)
}


@app.get("/", response_class=RedirectResponse)
def root():
    return RedirectResponse(url="/mobile")


@app.get("/mobile", response_class=HTMLResponse)
def mobile_home(request: Request, db: Session = Depends(get_db)):
    # Mock login: Assume E1001 for demo
    emp_id = "E1001"
    emp = db.get(Employee, emp_id)
    if not emp:
        return HTMLResponse("<h1>Demo Error: Employee E1001 not found (please check seed data)</h1>")

    today = date.today()
    
    # Get today's record
    today_record = db.execute(
        select(AttendanceRecord).where(and_(AttendanceRecord.emp_id == emp_id, AttendanceRecord.day == today))
    ).scalars().first()

    # Get recent history (last 5 days)
    history = db.execute(
        select(AttendanceRecord).where(
            and_(AttendanceRecord.emp_id == emp_id, AttendanceRecord.day < today)
        ).order_by(AttendanceRecord.day.desc()).limit(5)
    ).scalars().all()

    return templates.TemplateResponse("mobile_home.html", {
        "request": request, 
        "employee": emp, 
        "today_record": today_record, 
        "history": history
    })


class MarkAttendanceIn(BaseModel):
    emp_id: str
    date: str = None # Format YYYY-MM-DD, defaults to today if None


@app.post("/api/mark-attendance")
def mark_attendance_api(payload: MarkAttendanceIn, db: Session = Depends(get_db)):
    # Verify employee
    emp = db.get(Employee, payload.emp_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Determine target date
    if payload.date:
        try:
            target_date = datetime.strptime(payload.date, "%Y-%m-%d").date()
        except ValueError:
             raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = date.today()
    
    today = date.today()

    # --- SIMULATION & VALIDATION CHECKS ---
    global SIMULATION_STATE
    
    # 1. System Lockout (Manual Override)
    if SIMULATION_STATE == "LOCKOUT":
        raise HTTPException(status_code=400, detail="LOCKOUT_BLOCK")

    # 2. Weekend/Holiday Validation
    # Rules: Sat(5)/Sun(6) OR in INDIAN_HOLIDAYS OR Manual HOLIDAY state
    is_weekend = target_date.weekday() > 4
    is_holiday = (target_date.month, target_date.day) in INDIAN_HOLIDAYS
    
    # Validation Logic:
    # IF (Weekend OR Holiday) AND (State is NOT "UNLOCK_RESTRICTION") -> BLOCK
    # "UNLOCK_RESTRICTION" allows working on these days (simulating Atom approval)
    
    if (is_weekend or is_holiday or SIMULATION_STATE == "HOLIDAY"):
        if SIMULATION_STATE != "UNLOCK_RESTRICTION":
            raise HTTPException(status_code=400, detail="HOLIDAY_BLOCK")
        
    # 3. Date Validation (Past/Future)
    # We enforce this strictly for the demo (no backdated allowed even with unlock, usually)
    # OR we could allow backdated with unlock? Typically Unlock is for "Restricted Days".
    # Let's keep Past/Future strict for simplicity unless user asks.
    if target_date < today:
        raise HTTPException(status_code=400, detail="PAST_DATE_BLOCK")
    if target_date > today:
        raise HTTPException(status_code=400, detail="FUTURE_DATE_BLOCK")
    # -------------------------
    
    # Check if already marked
    existing = db.execute(
        select(AttendanceRecord).where(and_(
            AttendanceRecord.emp_id == payload.emp_id, 
            AttendanceRecord.day == target_date
        ))
    ).scalars().first()

    if existing:
        existing.status = "PRESENT"
        existing.last_updated_by = payload.emp_id
        existing.last_updated_at = datetime.utcnow()
        existing.source_system = "MOBILE_APP"
    else:
        # Create new record
        new_rec = AttendanceRecord(
            emp_id=payload.emp_id,
            day=target_date,
            status="PRESENT",
            source_system="MOBILE_APP",
            last_updated_by=payload.emp_id,
            last_updated_at=datetime.utcnow()
        )
        db.add(new_rec)
    
    db.commit()
    return {"status": "success", "message": "Marked present"}


# -----------------------------
# Admin UI
# -----------------------------

@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_ui(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.post("/admin/login")
def admin_login(username: str = Form(...), password: str = Form(...)):
    # Mock Auth
    if username == "admin" and password == "admin":
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(key="admin_session", value="true")
        return response
    return HTMLResponse("Invalid credentials", status_code=401)

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    # Check auth
    if not request.cookies.get("admin_session"):
        return RedirectResponse(url="/admin/login")

    # Fetch Stats
    total_emps = db.query(Employee).count()
    today = date.today()
    present_today = db.query(AttendanceRecord).filter(
        AttendanceRecord.day == today, 
        AttendanceRecord.status == "PRESENT"
    ).count()
    
    reqs = db.execute(select(AttendanceChangeRequest).order_by(AttendanceChangeRequest.created_at.desc())).scalars().all()
    pending_count = len([r for r in reqs if r.status == "PENDING_APPROVAL"])
    
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request, 
        "requests": reqs,
        "total_employees": total_emps,
        "present_today": present_today,
        "pending_requests": pending_count
    })

@app.get("/admin/requests/{request_id}", response_class=HTMLResponse)
def admin_request_detail(request_id: int, request: Request, db: Session = Depends(get_db)):
    if not request.cookies.get("admin_session"):
        return RedirectResponse(url="/admin/login")

    req = db.get(AttendanceChangeRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    employee = db.get(Employee, req.emp_id)
    audit_logs = req.audit_events
    
    return templates.TemplateResponse("request_detail.html", {
        "request": request,
        "req": req,
        "employee": employee,
        "audit_logs": audit_logs
    })

@app.get("/api/employees-list", response_model=List[EmployeeOut])
def api_employees_list(db: Session = Depends(get_db)):
    return db.query(Employee).all()

@app.get("/admin/employees/{emp_id}", response_class=HTMLResponse)
def admin_employee_detail(request: Request, emp_id: str, db: Session = Depends(get_db)):
    # Check auth
    if not request.cookies.get("admin_session"):
        return RedirectResponse(url="/admin/login")

    emp = db.get(Employee, emp_id)
    if not emp:
         raise HTTPException(status_code=404, detail="Employee not found")

    # History
    history = db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.emp_id == emp_id
        ).order_by(AttendanceRecord.day.desc()).limit(30)
    ).scalars().all()

    # Change Requests (Audit Log)
    start_history = db.execute(
        select(AttendanceChangeRequest)
        .where(AttendanceChangeRequest.emp_id == emp_id)
        .order_by(AttendanceChangeRequest.created_at.desc())
    ).scalars().all()

    return templates.TemplateResponse("employee_detail.html", {
        "request": request, 
        "emp": emp, 
        "history": history,
        "change_requests": start_history
    })



@app.get("/admin/requests/{request_id}", response_class=HTMLResponse)
def admin_request_detail(request: Request, request_id: int, db: Session = Depends(get_db)):
    req = db.get(AttendanceChangeRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return templates.TemplateResponse(
        "request_detail.html",
        {"request": request, "req": req, "audit": req.audit_events},
    )

@app.post("/admin/requests/{request_id}/approve")
def admin_approve(request_id: int, actor_emp_id: str = Form(...), comment: str = Form(""), db: Session = Depends(get_db)):
    approve_request(request_id, RequestActionIn(actor_emp_id=actor_emp_id, comment=comment), db)
    return RedirectResponse(url=f"/admin/requests/{request_id}", status_code=303)


@app.post("/admin/requests/{request_id}/reject")
def admin_reject(request_id: int, actor_emp_id: str = Form(...), comment: str = Form(""), db: Session = Depends(get_db)):
    reject_request(request_id, RequestActionIn(actor_emp_id=actor_emp_id, comment=comment), db)
    return RedirectResponse(url=f"/admin/requests/{request_id}", status_code=303)

