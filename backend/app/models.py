import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, String, Text

from .db import Base, init_db


def _uid() -> str:
    return uuid.uuid4().hex[:12]


class Complaint(Base):
    """A complaint committed to the QMS ledger. `form` and `risk` are stored as
    JSON so the AI schema can evolve without a migration per field."""

    __tablename__ = "complaints"

    id = Column(String(12), primary_key=True, default=_uid)
    complaint_no = Column(String(32), unique=True, index=True)
    product_name = Column(String(255), index=True)
    batch_number = Column(String(64), index=True)
    customer_name = Column(String(255))
    severity = Column(String(32))
    status = Column(String(32), default="Logged")
    form = Column(JSON)
    risk = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditEvent(Base):
    """Append-only trail: every AI mutation of the form is recorded with the
    prompt that caused it. Pharma QMS needs this (ALCOA+ / 21 CFR Part 11)."""

    __tablename__ = "audit_events"

    id = Column(String(12), primary_key=True, default=_uid)
    session_id = Column(String(64), index=True)
    actor = Column(String(32))
    action = Column(String(64))
    detail = Column(Text)
    changed_fields = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


init_db()
