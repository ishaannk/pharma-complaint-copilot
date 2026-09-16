"""The LangGraph workflow behind the Copilot.

    ingest -> route -+-> log_complaint  -+
                     +-> edit_complaint -+-> risk_assess -> post_checks -> compose_reply
                     +-> answer_query   ------------------------------------------------>

Three mandatory tools map onto these nodes (log / edit / document-extraction, the last
being `ingest` + `log_complaint`). Everything after the fork is shared, so a correction
re-runs the risk assessment exactly like a fresh complaint does.
"""
from __future__ import annotations

import json
import re
import time
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ..schemas import CRITICAL_FIELDS, FIELD_KEYS, FORM_FIELDS
from . import prompts
from .llm import EXTRACTOR_ID, REASONER_ID, extractor, json_call, reasoner, text_call

LABELS = {k: label for k, label, _ in FORM_FIELDS}


def _extend(old: list, new: list) -> list:
    return (old or []) + (new or [])


class AgentState(TypedDict, total=False):
    message: str
    document_text: str
    document_name: str
    form: dict[str, str]
    risk: dict[str, Any]
    intent: str
    changed_fields: list[str]
    provenance: dict[str, str]
    completeness: dict[str, Any]
    duplicates: list[dict[str, Any]]
    reply: str
    trace: Annotated[list[dict[str, Any]], _extend]


NULLISH = {"n/a", "na", "none", "null", "unknown", "not provided", "not specified", "-"}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


# Models are asked for field keys, but some return the human label instead
# ("Affected Quantity" for affected_quantity). Without this the value is silently
# dropped -- the worst kind of bug here, because the form just looks incomplete.
_ALIASES = {_norm(k): k for k in FIELD_KEYS}
_ALIASES.update({_norm(label): k for k, label, _ in FORM_FIELDS})


def _normalize_keys(data: dict) -> dict:
    """Map whatever the model called a field back onto our field keys."""
    out = {}
    for raw_key, value in (data or {}).items():
        key = _ALIASES.get(_norm(raw_key))
        if key and key not in out:
            out[key] = value
    return out


def _clean(value: Any) -> str:
    """Models like to fill blanks with 'N/A' or 'null'. Those are not data."""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in NULLISH else text


def _source_text(state: AgentState) -> str:
    parts = []
    if state.get("document_text"):
        name = state.get("document_name") or "file"
        parts.append("--- UPLOADED DOCUMENT (" + name + ") ---\n" + state["document_text"])
    if state.get("message"):
        parts.append("--- USER MESSAGE ---\n" + state["message"])
    return "\n\n".join(parts)


def _form_snapshot(form: dict[str, str]) -> str:
    return json.dumps({LABELS[k]: form.get(k, "") for k in FIELD_KEYS}, indent=2)


def _step(name: str, started: float, **extra) -> list[dict[str, Any]]:
    return [{"node": name, "ms": int((time.time() - started) * 1000), **extra}]


# -- nodes --------------------------------------------------------------------


def ingest(state: AgentState) -> AgentState:
    """Document Extraction Tool, first half: note that a document is in play."""
    t = time.time()
    has_doc = bool(state.get("document_text"))
    return {
        "form": state.get("form") or {k: "" for k in FIELD_KEYS},
        "trace": _step(
            "ingest", t,
            document=state.get("document_name") if has_doc else None,
            chars=len(state.get("document_text") or ""),
        ),
    }


def route(state: AgentState) -> AgentState:
    """Decide which tool to run. A document upload is always a log."""
    t = time.time()
    if state.get("document_text"):
        return {"intent": "log", "trace": _step("route", t, intent="log", reason="document uploaded")}

    if not any(state["form"].get(k) for k in FIELD_KEYS):
        return {"intent": "log", "trace": _step("route", t, intent="log", reason="form empty")}

    try:
        out = json_call(
            extractor,
            prompts.ROUTER,
            "Current form:\n" + _form_snapshot(state["form"]) + "\n\nUser message:\n" + state["message"],
        )
        intent = out.get("intent", "edit")
        reason = out.get("reason", "")
    except Exception as exc:  # a routing failure must not kill the turn
        intent, reason = "edit", "router fallback (" + type(exc).__name__ + ")"

    if intent not in {"log", "edit", "query"}:
        intent = "edit"
    return {"intent": intent, "trace": _step("route", t, intent=intent, reason=reason)}


def log_complaint(state: AgentState) -> AgentState:
    """Tool 1 & 3: extract a complete complaint from a prompt or a document."""
    t = time.time()
    data = _normalize_keys(json_call(extractor, prompts.EXTRACT, _source_text(state)))
    form = {k: _clean(data.get(k)) for k in FIELD_KEYS}

    origin = "document:" + state["document_name"] if state.get("document_text") else "prompt"
    changed = [k for k in FIELD_KEYS if form[k]]
    return {
        "form": form,
        "changed_fields": changed,
        "provenance": {k: origin for k in changed},
        "trace": _step("log_complaint", t, model=EXTRACTOR_ID, fields_filled=len(changed)),
    }


def edit_complaint(state: AgentState) -> AgentState:
    """Tool 2: apply a natural-language correction, preserving everything else.

    The model returns only a patch, so fields it never mentions cannot be clobbered --
    the usual failure mode when you re-extract the whole form on every correction.
    """
    t = time.time()
    patch = _normalize_keys(json_call(
        extractor,
        prompts.PATCH,
        "Current form:\n" + _form_snapshot(state["form"]) + "\n\nUser correction:\n" + state["message"],
    ))

    form = dict(state["form"])
    changed = []
    for key in FIELD_KEYS:
        if key not in patch:
            continue
        value = _clean(patch[key])
        if value and value != form.get(key):
            form[key] = value
            changed.append(key)

    provenance = dict(state.get("provenance") or {})
    provenance.update({k: "correction" for k in changed})
    return {
        "form": form,
        "changed_fields": changed,
        "provenance": provenance,
        "trace": _step("edit_complaint", t, model=EXTRACTOR_ID, changed=changed),
    }


def answer_query(state: AgentState) -> AgentState:
    """Questions get an answer, never a form mutation."""
    t = time.time()
    answer = text_call(
        reasoner,
        prompts.QUERY,
        "Complaint form:\n" + _form_snapshot(state["form"])
        + "\n\nRisk assessment:\n" + json.dumps(state.get("risk") or {}, indent=2)
        + "\n\nQuestion:\n" + state["message"],
    )
    return {
        "reply": answer,
        "changed_fields": [],
        "trace": _step("answer_query", t, model=REASONER_ID),
    }


def risk_assess(state: AgentState) -> AgentState:
    """AI Risk Classification + Root Cause + CAPA, on the 70b reasoning model."""
    t = time.time()
    try:
        data = json_call(reasoner, prompts.RISK, "Complaint:\n" + _form_snapshot(state["form"]))
    except Exception as exc:
        return {"risk": state.get("risk") or {}, "trace": _step("risk_assess", t, error=str(exc)[:120])}

    try:
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.6))))
    except (TypeError, ValueError):
        confidence = 0.6

    risk = {
        "severity_suggested": _clean(data.get("severity_suggested")) or "Major",
        "suggested_next_action": _clean(data.get("suggested_next_action")),
        "initial_risk_assessment": _clean(data.get("initial_risk_assessment")),
        "probable_root_cause": _clean(data.get("probable_root_cause")),
        "capa_recommendation": _clean(data.get("capa_recommendation")),
        "regulatory_reportable": _clean(data.get("regulatory_reportable")),
        "summary": _clean(data.get("summary")),
        "confidence": confidence,
    }
    return {
        "risk": risk,
        "trace": _step(
            "risk_assess", t, model=REASONER_ID,
            severity=risk["severity_suggested"], confidence=confidence,
        ),
    }


def post_checks(state: AgentState) -> AgentState:
    """Completeness Checker + Duplicate Detection. Deterministic on purpose -- these
    are cheap rules, and a QA reviewer must be able to trust them exactly."""
    t = time.time()
    form = state["form"]

    missing = [LABELS[k] for k in FIELD_KEYS if not form.get(k)]
    blocking = [LABELS[k] for k in CRITICAL_FIELDS if not form.get(k)]
    completeness = {
        "score": round(100 * (len(FIELD_KEYS) - len(missing)) / len(FIELD_KEYS)),
        "missing_fields": missing,
        "blocking": blocking,
        "ready_to_commit": not blocking,
    }

    from ..dedupe import find_duplicates  # local import keeps this module DB-agnostic

    duplicates = find_duplicates(form)
    return {
        "completeness": completeness,
        "duplicates": duplicates,
        "trace": _step("post_checks", t, completeness=completeness["score"], duplicates=len(duplicates)),
    }


def compose_reply(state: AgentState) -> AgentState:
    """One short confirmation, naming what actually moved on screen."""
    t = time.time()
    changed = state.get("changed_fields") or []
    if not changed:
        return {
            "reply": "I could not find anything to change in that message. Could you restate the "
                     "detail you want corrected?",
            "trace": _step("compose_reply", t, skipped=True),
        }

    changes = ", ".join(LABELS[k] + ' = "' + state["form"][k] + '"' for k in changed)
    action = "Extracted a new complaint" if state["intent"] == "log" else "Applied a correction"
    try:
        reply = text_call(
            reasoner,
            prompts.REPLY,
            action + " from: " + (state.get("document_name") or "the user message") + ".\n"
            + "Fields set: " + changes + "\n"
            + "Severity assessed: " + (state.get("risk") or {}).get("severity_suggested", ""),
        )
    except Exception:
        reply = action + ". Updated " + str(len(changed)) + " field(s): " + changes + "."
    return {"reply": reply, "trace": _step("compose_reply", t, model=REASONER_ID)}


# -- wiring -------------------------------------------------------------------


def _fork(state: AgentState) -> str:
    return state["intent"]


def build_graph():
    g = StateGraph(AgentState)
    for name, fn in [
        ("ingest", ingest),
        ("route", route),
        ("log_complaint", log_complaint),
        ("edit_complaint", edit_complaint),
        ("answer_query", answer_query),
        ("risk_assess", risk_assess),
        ("post_checks", post_checks),
        ("compose_reply", compose_reply),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "ingest")
    g.add_edge("ingest", "route")
    g.add_conditional_edges("route", _fork, {
        "log": "log_complaint",
        "edit": "edit_complaint",
        "query": "answer_query",
    })
    g.add_edge("log_complaint", "risk_assess")
    g.add_edge("edit_complaint", "risk_assess")
    g.add_edge("risk_assess", "post_checks")
    g.add_edge("post_checks", "compose_reply")
    g.add_edge("compose_reply", END)
    g.add_edge("answer_query", END)
    return g.compile()


graph = build_graph()
