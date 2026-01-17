from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class EmployeeOut(BaseModel):
    emp_id: str
    name: str
    location: Optional[str] = None
    cost_center: Optional[str] = None
    manager_emp_id: Optional[str] = None


class AttendanceRecordOut(BaseModel):
    id: int
    emp_id: str
    day: date
    status: str
    source_system: str
    last_updated_by: Optional[str] = None
    last_updated_at: datetime


class RequestCreateIn(BaseModel):
    emp_id: str
    request_type: str = Field(..., description="UNLOCK | CORRECT_MARKING | HOLIDAY_EXCEPTION")
    date_start: date
    date_end: date
    current_status: Optional[str] = None
    desired_status: Optional[str] = None
    reason_category: Optional[str] = None
    reason_text: Optional[str] = None


class RequestActionIn(BaseModel):
    actor_emp_id: str
    comment: Optional[str] = None


class AuditEventOut(BaseModel):
    id: int
    request_id: int
    actor_emp_id: Optional[str] = None
    action: str
    comment: Optional[str] = None
    created_at: datetime


class RequestOut(BaseModel):
    id: int
    emp_id: str
    request_type: str
    date_start: date
    date_end: date
    current_status: Optional[str] = None
    desired_status: Optional[str] = None
    reason_category: str
    reason_text: Optional[str] = None
    approver_emp_id: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class RequestWithAuditOut(RequestOut):
    audit_events: List[AuditEventOut] = []




from pydantic import BaseModel, model_validator
import json

class AtomicworkSyncIn(BaseModel):
    emp_id: str
    date: date
    status: str
    reason: str
    approval_note: str

    @model_validator(mode='before')
    @classmethod
    def parse_payload(cls, data):
        # 1. Handle Double-Encoded JSON (String -> Dict)
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                pass
        
        # 2. Handle Flexible Date Formats
        if isinstance(data, dict) and "date" in data:
            raw_date = data["date"]
            if isinstance(raw_date, str):
                try:
                    from dateutil import parser
                    dt = parser.parse(raw_date, dayfirst=True)
                    data["date"] = dt.date()
                except Exception:
                    pass
        
        return data
