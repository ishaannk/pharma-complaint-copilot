"""Duplicate Complaint Detection (bonus feature).

Rule-based, not an embedding index: at QMS volumes an exact batch collision is the
signal that actually matters to a QA reviewer, and a deterministic rule is one they
can defend in an audit. Token overlap on the defect text catches the rest.
"""
from __future__ import annotations

import re

from .db import SessionLocal
from .models import Complaint

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "for", "to", "with", "is", "are",
    "was", "were", "be", "been", "has", "have", "had", "reported", "complaint", "customer",
    "batch", "product", "issue", "found", "this", "that", "from", "by", "at", "as", "it",
}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in STOPWORDS and len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_duplicates(form: dict[str, str], limit: int = 3) -> list[dict]:
    batch = (form.get("batch_number") or "").strip()
    product = (form.get("product_name") or "").strip()
    if not batch and not product:
        return []

    defect = _tokens(form.get("complaint_description", "") + " " + form.get("complaint_category", ""))
    hits = []

    with SessionLocal() as db:
        # Only pull candidates that already share a batch or a product -- no full scan.
        query = db.query(Complaint)
        filters = []
        if batch:
            filters.append(Complaint.batch_number.ilike(batch))
        if product:
            filters.append(Complaint.product_name.ilike("%" + product + "%"))
        from sqlalchemy import or_

        rows = query.filter(or_(*filters)).order_by(Complaint.created_at.desc()).limit(50).all()

        for row in rows:
            overlap = _jaccard(defect, _tokens((row.form or {}).get("complaint_description", "")))
            same_batch = batch and (row.batch_number or "").strip().lower() == batch.lower()

            if same_batch and overlap >= 0.3:
                score, reason = 95, "Same batch and near-identical defect description"
            elif same_batch:
                score, reason = 75, "Same batch / lot number already has an open complaint"
            elif overlap >= 0.5:
                score, reason = 60, "Same product with a very similar defect description"
            else:
                continue

            hits.append({
                "complaint_no": row.complaint_no,
                "product_name": row.product_name or "",
                "batch_number": row.batch_number or "",
                "reason": reason,
                "score": score,
            })

    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:limit]
