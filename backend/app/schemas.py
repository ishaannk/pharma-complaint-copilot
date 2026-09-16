from typing import Any, Literal

from pydantic import BaseModel, Field

# Field labels mirror the demo video's form, section by section. FORM_FIELDS is
# the single source of truth: the LLM prompts, the completeness checker and the
# React form are all generated from it.
FORM_FIELDS: list[tuple[str, str, str]] = [
    ("complaint_source", "Complaint Source", "1. Origin & Customer Details"),
    ("customer_name", "Customer Name", "1. Origin & Customer Details"),
    ("complaint_date", "Complaint Date", "1. Origin & Customer Details"),
    ("product_name", "Product Name", "2. Product & Batch Identification"),
    ("product_strength", "Product Strength / Grade", "2. Product & Batch Identification"),
    ("batch_number", "Batch / Lot Number", "2. Product & Batch Identification"),
    ("affected_quantity", "Affected Quantity", "2. Product & Batch Identification"),
    ("manufacturing_date", "Manufacturing Date", "2. Product & Batch Identification"),
    ("expiry_date", "Expiry Date", "2. Product & Batch Identification"),
    ("originating_site_block", "Originating Site Block", "3. Facility & Material Impact"),
    ("impacted_npm", "Impacted Non-Product Materials (NPM)", "3. Facility & Material Impact"),
    ("complaint_category", "Complaint Category", "4. Defect Analysis"),
    ("complaint_description", "Complaint Description", "4. Defect Analysis"),
]

FIELD_KEYS = [k for k, _, _ in FORM_FIELDS]

# Fields a QA reviewer must have before the complaint can be committed.
CRITICAL_FIELDS = [
    "product_name",
    "batch_number",
    "customer_name",
    "complaint_description",
    "complaint_category",
]


class ComplaintForm(BaseModel):
    complaint_source: str = ""
    customer_name: str = ""
    complaint_date: str = ""
    product_name: str = ""
    product_strength: str = ""
    batch_number: str = ""
    affected_quantity: str = ""
    manufacturing_date: str = ""
    expiry_date: str = ""
    originating_site_block: str = ""
    impacted_npm: str = ""
    complaint_category: str = ""
    complaint_description: str = ""


class RiskAssessment(BaseModel):
    """The AI Copilot Risk Assessment panel plus the bonus AI features."""

    severity_suggested: str = ""          # Critical | Major | Minor
    suggested_next_action: str = ""
    initial_risk_assessment: str = ""
    probable_root_cause: str = ""         # bonus: Root Cause Recommendation
    capa_recommendation: str = ""         # bonus: CAPA Recommendation
    regulatory_reportable: str = ""       # bonus: field-alert / recall exposure
    summary: str = ""                     # bonus: Complaint Summary
    confidence: float = 0.0


class Completeness(BaseModel):
    """Bonus: Complaint Completeness Checker."""

    score: int = 0
    missing_fields: list[str] = Field(default_factory=list)
    blocking: list[str] = Field(default_factory=list)
    ready_to_commit: bool = False


class DuplicateHit(BaseModel):
    """Bonus: Duplicate Complaint Detection."""

    complaint_no: str
    product_name: str
    batch_number: str
    reason: str
    score: int


class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str = ""
    form: ComplaintForm = Field(default_factory=ComplaintForm)
    risk: RiskAssessment = Field(default_factory=RiskAssessment)


class ChatResponse(BaseModel):
    reply: str
    intent: Literal["log", "edit", "query", "error"] = "query"
    form: ComplaintForm
    risk: RiskAssessment
    changed_fields: list[str] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)
    completeness: Completeness = Field(default_factory=Completeness)
    duplicates: list[DuplicateHit] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
