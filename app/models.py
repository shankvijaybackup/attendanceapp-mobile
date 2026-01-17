from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Optional, List

from sqlalchemy import String, DateTime, Date, ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LEAVE = "LEAVE"
    HOLIDAY = "HOLIDAY"
    WEEKLY_OFF = "WEEKLY_OFF"


class RequestType(str, Enum):
    UNLOCK = "UNLOCK"
    CORRECT_MARKING = "CORRECT_MARKING"
    HOLIDAY_EXCEPTION = "HOLIDAY_EXCEPTION"


class RequestStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    FAILED = "FAILED"


class ReasonCategory(str, Enum):
    MISTAKE = "MISTAKE"
    HOLIDAY_WORK = "HOLIDAY_WORK"
    SYSTEM_ISSUE = "SYSTEM_ISSUE"
    MANAGER_ON_LEAVE = "MANAGER_ON_LEAVE"
    OTHER = "OTHER"


class Employee(Base):
    __tablename__ = "employees"

    emp_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cost_center: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    device: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    manager_emp_id: Mapped[Optional[str]] = mapped_column(
        String(32), ForeignKey("employees.emp_id"), nullable=True
    )

    # Correct SQLAlchemy typing: Optional["Employee"]
    manager: Mapped[Optional["Employee"]] = relationship(
        remote_side=[emp_id], backref="reports"
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    emp_id: Mapped[str] = mapped_column(String(32), ForeignKey("employees.emp_id"))
    day: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32))
    source_system: Mapped[str] = mapped_column(String(50), default="SAP_MOCK")
    last_updated_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee: Mapped[Employee] = relationship()


class AttendanceChangeRequest(Base):
    __tablename__ = "attendance_change_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    emp_id: Mapped[str] = mapped_column(String(32), ForeignKey("employees.emp_id"))
    request_type: Mapped[str] = mapped_column(String(40))

    date_start: Mapped[date] = mapped_column(Date)
    date_end: Mapped[date] = mapped_column(Date)

    current_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    desired_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    reason_category: Mapped[str] = mapped_column(String(40), default=ReasonCategory.OTHER.value)
    reason_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    approver_emp_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    status: Mapped[str] = mapped_column(String(40), default=RequestStatus.PENDING_APPROVAL.value)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee: Mapped[Employee] = relationship(foreign_keys=[emp_id])

    audit_events: Mapped[List["AuditEvent"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="AuditEvent.created_at",
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("attendance_change_requests.id"))

    actor_emp_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    request: Mapped[AttendanceChangeRequest] = relationship(back_populates="audit_events")
