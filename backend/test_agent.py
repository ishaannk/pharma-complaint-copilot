"""Self-check for the logic that is not the LLM.

    python backend/test_agent.py

Covers the parts that silently corrupt a complaint if they break: the JSON salvage
in llm.py, the patch-merge that must never drop a field, the completeness rules and
duplicate scoring. The model calls themselves are exercised by the demo, not here --
asserting on generated prose is a test that fails for the wrong reasons.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Point at a throwaway DB before anything imports the engine.
os.environ["database_url"] = "sqlite:///" + tempfile.mkdtemp().replace("\\", "/") + "/test.db"
os.environ.setdefault("groq_api_key", "test-key-not-used")

from app.agent.llm import _first_json_object  # noqa: E402
from app.dedupe import _jaccard, _tokens, find_duplicates  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import Complaint  # noqa: E402
from app.schemas import FIELD_KEYS  # noqa: E402


def test_json_salvage():
    """Models wrap JSON in prose or fences; the brace scanner must still find it."""
    assert _first_json_object('Here you go: {"a": 1} hope that helps') == '{"a": 1}'
    # A brace inside a string must not end the object early.
    assert _first_json_object('{"note": "closing } brace", "b": 2}') == '{"note": "closing } brace", "b": 2}'
    # Nested objects.
    assert _first_json_object('x {"a": {"b": 1}} y') == '{"a": {"b": 1}}'
    # An escaped quote must not terminate the string.
    assert _first_json_object(r'{"q": "she said \"hi\" }", "c": 3}') == r'{"q": "she said \"hi\" }", "c": 3}'
    print("ok  json salvage")


def test_patch_merge_preserves_fields():
    """The demo's core promise: a correction changes only what was mentioned."""
    from app.agent.graph import _clean

    form = {k: "" for k in FIELD_KEYS}
    form.update({
        "product_name": "Amoxicillin Capsules",
        "product_strength": "500 mg",
        "batch_number": "AMX240602",
        "expiry_date": "February 2028",
    })
    patch = {"batch_number": "BMX240602", "affected_quantity": "48 capsules", "product_name": "N/A"}

    merged, changed = dict(form), []
    for key in FIELD_KEYS:
        if key not in patch:
            continue
        value = _clean(patch[key])
        if value and value != merged.get(key):
            merged[key] = value
            changed.append(key)

    assert changed == ["batch_number", "affected_quantity"], changed
    assert merged["batch_number"] == "BMX240602"
    assert merged["affected_quantity"] == "48 capsules"
    # "N/A" is not data -- it must not wipe a real value.
    assert merged["product_name"] == "Amoxicillin Capsules"
    assert merged["expiry_date"] == "February 2028"
    print("ok  patch merge preserves untouched fields")


def test_key_normalization():
    """Regression: google/gemma-3-12b-it returned {"Affected Quantity": "48 capsules"}
    -- the label, not the field key. The merge loop reads FIELD_KEYS, so the value was
    silently dropped and the form just looked incomplete. Any casing or spacing of a
    known field name must map back onto its key."""
    from app.agent.graph import _normalize_keys

    got = _normalize_keys({
        "Affected Quantity": "48 capsules",   # label
        "batch_number": "BMX240602",          # key
        "Batch / Lot Number": "IGNORED",      # duplicate of the above, key wins
        "product name": "Amoxicillin",        # loose spacing
        "PRODUCT_STRENGTH": "500 mg",         # casing
        "invented_field": "x",                # unknown -> dropped
    })
    assert got["affected_quantity"] == "48 capsules"
    assert got["batch_number"] == "BMX240602", "first spelling wins, no clobbering"
    assert got["product_name"] == "Amoxicillin"
    assert got["product_strength"] == "500 mg"
    assert "invented_field" not in got
    assert set(got) <= set(FIELD_KEYS)
    print("ok  model key/label normalization")


def test_clean_rejects_filler():
    from app.agent.graph import _clean

    for filler in ["N/A", "n/a", "None", "null", "  Not Provided  ", "-", "unknown"]:
        assert _clean(filler) == "", filler
    assert _clean("  BMX240602 ") == "BMX240602"
    assert _clean(None) == ""
    print("ok  filler values rejected")


def test_completeness():
    from app.agent.graph import post_checks

    form = {k: "" for k in FIELD_KEYS}
    empty = post_checks({"form": form})["completeness"]
    assert empty["score"] == 0
    assert not empty["ready_to_commit"], "an empty form must never be committable"

    form.update({
        "product_name": "Metformin API", "batch_number": "MFH260712A",
        "customer_name": "ABC Formulations", "complaint_description": "Foreign matter found.",
        "complaint_category": "Foreign Matter Contamination",
    })
    partial = post_checks({"form": form})["completeness"]
    assert partial["ready_to_commit"], "all critical fields present -> committable"
    assert partial["blocking"] == []
    assert 0 < partial["score"] < 100
    assert "Expiry Date" in partial["missing_fields"]
    print("ok  completeness scoring and commit gate")


def test_duplicate_detection():
    with SessionLocal() as db:
        db.add(Complaint(
            complaint_no="CC-2026-00001", product_name="Amoxicillin Capsules",
            batch_number="AMX240602", customer_name="Apollo Pharmacy", severity="Major",
            form={"complaint_description": "Discolored capsules found in a sealed bottle."},
            risk={},
        ))
        db.commit()

    same_batch = find_duplicates({
        "batch_number": "amx240602",  # casing must not matter
        "product_name": "Amoxicillin Capsules",
        "complaint_description": "Discolored capsules found in a sealed bottle.",
        "complaint_category": "Product Defect - Discoloration",
    })
    assert same_batch and same_batch[0]["complaint_no"] == "CC-2026-00001"
    assert same_batch[0]["score"] == 95, same_batch[0]

    unrelated = find_duplicates({
        "batch_number": "PNT260521B", "product_name": "Pantoprazole Tablets",
        "complaint_description": "Blister foil seal lifted at the edges.",
        "complaint_category": "Packaging Defect",
    })
    assert unrelated == [], unrelated

    assert find_duplicates({"batch_number": "", "product_name": ""}) == []
    print("ok  duplicate detection")


def test_jaccard():
    assert _jaccard(set(), {"a"}) == 0.0
    assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert _tokens("The batch of capsules was reported") == {"capsules"}
    print("ok  token overlap")


if __name__ == "__main__":
    test_json_salvage()
    test_key_normalization()
    test_clean_rejects_filler()
    test_patch_merge_preserves_fields()
    test_completeness()
    test_duplicate_detection()
    test_jaccard()
    print("\nall checks passed")
