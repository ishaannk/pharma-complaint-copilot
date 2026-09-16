"""FastAPI surface for the AIVOA complaint module.

    POST /api/chat      prompt  -> log / edit / query   (multipart: optional document)
    POST /api/commit    write the complaint to the QMS ledger
    GET  /api/complaints  ledger listing
    GET  /api/audit/{session_id}  append-only AI action trail
    GET  /api/graph     the LangGraph topology, for the UI's workflow panel
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from .config import CORS_ORIGINS, DATABASE_URL, EXTRACTION_MODEL, LLM_PROVIDER, REASONING_MODEL
from .db import get_db
from .extract import document_to_text
from .models import AuditEvent, Complaint
from .schemas import ChatResponse, ComplaintForm, RiskAssessment

log = logging.getLogger("aivoa")

app = FastAPI(title="AIVOA Complaint Management", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_UPLOAD = 10 * 1024 * 1024  # 10 MB, matching the reference UI's stated limit


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm_provider": LLM_PROVIDER,
        "extraction_model": EXTRACTION_MODEL,
        "reasoning_model": REASONING_MODEL,
        "database": DATABASE_URL.split("://", 1)[0],
    }


@app.get("/api/graph")
def graph_topology():
    """Rendered by the UI so the LangGraph run is visible, not just described."""
    return {
        "nodes": [
            {"id": "ingest", "label": "Ingest", "note": "document -> text"},
            {"id": "route", "label": "Router", "note": "log / edit / query", "model": EXTRACTION_MODEL},
            {"id": "log_complaint", "label": "Log Complaint", "note": "tool 1 + 3", "model": EXTRACTION_MODEL},
            {"id": "edit_complaint", "label": "Edit Complaint", "note": "tool 2 (patch)", "model": EXTRACTION_MODEL},
            {"id": "answer_query", "label": "Answer Query", "note": "read-only", "model": REASONING_MODEL},
            {"id": "risk_assess", "label": "Risk Assess", "note": "severity + RCA + CAPA", "model": REASONING_MODEL},
            {"id": "post_checks", "label": "Post Checks", "note": "completeness + duplicates"},
            {"id": "compose_reply", "label": "Compose Reply", "model": REASONING_MODEL},
        ],
        "edges": [
            ["START", "ingest"], ["ingest", "route"],
            ["route", "log_complaint"], ["route", "edit_complaint"], ["route", "answer_query"],
            ["log_complaint", "risk_assess"], ["edit_complaint", "risk_assess"],
            ["risk_assess", "post_checks"], ["post_checks", "compose_reply"],
            ["compose_reply", "END"], ["answer_query", "END"],
        ],
    }


def _parse_json_field(raw: str | None, default: dict) -> dict:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    session_id: str = Form("default"),
    message: str = Form(""),
    form: str | None = Form(None),
    risk: str | None = Form(None),
    document: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    """Single entry point for all three mandatory tools.

    Multipart rather than JSON so the prompt and an optional document arrive in one
    request -- the demo uploads a PDF and types a sentence in the same turn.
    """
    document_text, document_name = "", None
    if document is not None and document.filename:
        raw = await document.read()
        if len(raw) > MAX_UPLOAD:
            raise HTTPException(413, "File exceeds the 10 MB limit.")
        try:
            document_text = document_to_text(document.filename, raw)
        except Exception as exc:
            raise HTTPException(422, str(exc)) from exc
        document_name = document.filename

    if not message.strip() and not document_text:
        raise HTTPException(400, "Send a message or a document.")

    current_form = ComplaintForm(**_parse_json_field(form, {})).model_dump()
    current_risk = RiskAssessment(**_parse_json_field(risk, {})).model_dump()

    from .agent.graph import graph  # imported lazily so /api/health works without a key

    try:
        state = graph.invoke({
            "message": message,
            "document_text": document_text,
            "document_name": document_name,
            "form": current_form,
            "risk": current_risk,
            "trace": [],
        })
    except Exception as exc:
        log.exception("graph failure")
        return ChatResponse(
            reply="The AI workflow failed on that request (" + type(exc).__name__ + "). "
                  "Your form is unchanged -- please try rephrasing.",
            intent="error",
            form=ComplaintForm(**current_form),
            risk=RiskAssessment(**current_risk),
        )

    changed = state.get("changed_fields") or []
    if changed:
        db.add(AuditEvent(
            session_id=session_id,
            actor="AIVOA Copilot",
            action=state.get("intent", "unknown"),
            detail=(document_name or message)[:1000],
            changed_fields=changed,
        ))
        db.commit()

    return ChatResponse(
        reply=state.get("reply", ""),
        intent=state.get("intent", "query"),
        form=ComplaintForm(**state["form"]),
        risk=RiskAssessment(**(state.get("risk") or current_risk)),
        changed_fields=changed,
        provenance=state.get("provenance") or {},
        completeness=state.get("completeness") or {},
        duplicates=state.get("duplicates") or [],
        trace=state.get("trace") or [],
    )


@app.post("/api/commit")
def commit(payload: dict, db: Session = Depends(get_db)):
    """Write the complaint to the QMS ledger and issue a complaint number."""
    form = ComplaintForm(**(payload.get("form") or {}))
    risk = RiskAssessment(**(payload.get("risk") or {}))

    if not form.product_name or not form.batch_number:
        raise HTTPException(422, "Product Name and Batch / Lot Number are required to commit.")

    year = datetime.utcnow().year
    seq = db.query(func.count(Complaint.id)).scalar() + 1
    complaint_no = "CC-" + str(year) + "-" + str(seq).zfill(5)

    row = Complaint(
        complaint_no=complaint_no,
        product_name=form.product_name,
        batch_number=form.batch_number,
        customer_name=form.customer_name,
        severity=risk.severity_suggested,
        form=form.model_dump(),
        risk=risk.model_dump(),
    )
    db.add(row)
    db.add(AuditEvent(
        session_id=payload.get("session_id", "default"),
        actor="QA User",
        action="commit",
        detail="Committed as " + complaint_no,
        changed_fields=[],
    ))
    db.commit()
    return {"complaint_no": complaint_no, "id": row.id, "status": row.status}


@app.get("/api/complaints")
def list_complaints(db: Session = Depends(get_db), limit: int = 50):
    rows = db.query(Complaint).order_by(Complaint.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "complaint_no": r.complaint_no,
            "product_name": r.product_name,
            "batch_number": r.batch_number,
            "customer_name": r.customer_name,
            "severity": r.severity,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@app.get("/api/audit/{session_id}")
def audit_trail(session_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(AuditEvent)
        .filter(AuditEvent.session_id == session_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "actor": r.actor,
            "action": r.action,
            "detail": r.detail,
            "changed_fields": r.changed_fields,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
