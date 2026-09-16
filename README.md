# AIVOA — AI-Powered Customer Complaint Management

A Customer Complaint intake module for pharmaceutical API and FDF manufacturing.
The QA reviewer never types into the form. They talk to the Copilot on the right, and
the Copilot fills, corrects and risk-assesses the complaint on the left.

Built for the AIVOA Round 1 AI Product Engineer assignment.

```
┌─────────────────────────────────┬───────────────────────────┐
│  Log Customer Complaint         │  AIVOA Copilot            │
│  1. Origin & Customer Details   │  ┌─────────────────────┐  │
│  2. Product & Batch ID          │  │ paste a complaint   │  │
│  3. Facility & Material Impact  │  │ or drop a PDF       │  │
│  4. Defect Analysis             │  └─────────────────────┘  │
│  ── AI Copilot Risk Assessment  │  LangGraph run — last turn│
│  [ Commit to QMS Ledger ]       │  route → log → risk → …   │
└─────────────────────────────────┴───────────────────────────┘
```

## Why a complaint module needs this

In a pharmaceutical QMS, a customer complaint is a regulated record. It starts as an
unstructured email or a scanned report from a distributor, and it has to become a
structured record with a batch number, a severity, and a decision about whether it is
reportable to a regulator — within days, because a Field Alert Report has a clock on it.

That transcription step is where the time goes and where the errors get in. This module
does the transcription and proposes the risk assessment; a QA reviewer signs it off.
**The AI proposes, a human commits.** Nothing is written to the ledger without a click.

## Quick start

```bash
# 1. Key — put openrouter_api_key in a .env at the repo root (or the parent folder)
cp .env.example .env

# 2. Backend
pip install -r backend/requirements.txt
cd backend && python -m uvicorn app.main:app --reload --port 8000

# 3. Frontend (second terminal)
cd frontend && npm install && npm run dev      # http://localhost:5173

# 4. Sample complaint documents for the upload demo
python samples/make_samples.py
```

The database defaults to SQLite so the repo runs with no infrastructure. For the
mandated SQL database, `docker compose up -d` and set
`database_url=postgresql+psycopg2://aivoa:aivoa@localhost:5432/aivoa_qms`.

## The three mandatory tools

| Tool | Say this | What happens |
|---|---|---|
| **Log Complaint** | *"Apollo Pharmacy reported discolored capsules in Amoxicillin Capsules 500 mg. Batch number AMX240602. Manufacturing date March 2026. Expiry date February 2028."* | Router sees an empty form → `log_complaint` extracts 9 fields → `risk_assess` returns **Major**, *Route to QA Investigation & Issue Replacement* |
| **Edit Complaint** | *"ah sorry the batch number is BMX240602 and affected quantity is 48 capsules"* | Router classifies `edit` → only those two fields change, highlighted green. Everything else is preserved |
| **Document Extraction** | Drop `samples/complaint_metformin_api_foreign_matter.pdf` | Extracts *Metformin Hydrochloride API / IP-BP / MFH260712A*, 92% complete, severity **Critical**, *Assess for Field Alert Report within 3 working days* |

After an upload you can still correct by voice of text: *"sorry the batch number is
CHG 260712A and affected quantity is 50 kg"* — the edit tool works the same on an
extracted complaint as on a typed one.

## The LangGraph workflow

```
START → ingest → route ─┬─► log_complaint  ─┐
                        ├─► edit_complaint ─┼─► risk_assess → post_checks → compose_reply → END
                        └─► answer_query ───────────────────────────────────────────────────► END
```

| Node | Model | Job |
|---|---|---|
| `ingest` | — | PDF / DOCX / EML / TXT → plain text |
| `route` | extraction | Classifies the turn as **log / edit / query** |
| `log_complaint` | extraction | Full-form extraction (tools 1 and 3) |
| `edit_complaint` | extraction | Returns a **patch**, not a whole form (tool 2) |
| `answer_query` | reasoning | Answers questions without touching the form |
| `risk_assess` | reasoning | Severity, root cause, CAPA, reportability |
| `post_checks` | — | Completeness + duplicates, deterministic |
| `compose_reply` | reasoning | The chat confirmation |

Three decisions worth defending in review:

**The edit node returns a patch, not a form.** The obvious implementation re-extracts
all thirteen fields on every correction, and the model quietly drops the ones the user
didn't mention. Returning `{"batch_number": "BMX240602"}` and merging it means an
unmentioned field is structurally incapable of being lost. `test_agent.py` asserts this.

**Two models, by job.** `route`, `log_complaint` and `edit_complaint` are structured
extraction at temperature 0 — the small model is faster and does not embellish.
`risk_assess` needs pharmaceutical judgment, so it runs on the larger model at 0.3.

**Completeness and duplicates are rules, not prompts.** A reviewer has to be able to
predict them, and an auditor has to be able to read them. A model that scores a form
88% one run and 91% the next is not a control.

## Bonus AI features

- **Complaint Completeness Checker** — score, missing-field chips, and a commit gate on the five fields a QA reviewer can't file without
- **AI Risk Classification** — Critical / Major / Minor against written criteria (patient-harm pathway, not vibes), with a confidence figure
- **Root Cause Recommendation** — names the likely process step, not "manufacturing error"
- **CAPA Recommendation** — one corrective and one preventive action
- **Duplicate Complaint Detection** — same batch, or same product with an overlapping defect description, checked against the ledger
- **Complaint Summary** — one line for the QA stand-up
- **Regulatory reportability** — flags Field Alert Report exposure, the thing with a deadline
- **Field provenance** — every field is tagged `from file`, `correction` or `edited` so a reviewer can see what the AI wrote versus what a human overrode
- **Audit trail** — every AI mutation is appended to `audit_events` with the prompt that caused it (ALCOA+ / 21 CFR Part 11 thinking)
- **Live LangGraph trace** — which nodes ran, which model, how many ms, under the chat

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/chat` | All three tools. Multipart: `message`, `form`, `risk`, optional `document` |
| `POST` | `/api/commit` | Write to the ledger, issue `CC-YYYY-NNNNN` |
| `GET` | `/api/complaints` | Ledger listing |
| `GET` | `/api/audit/{session_id}` | Append-only AI action trail |
| `GET` | `/api/graph` | Graph topology, rendered by the UI |
| `GET` | `/api/health` | Status and the models actually in use |

`/api/chat` is multipart rather than JSON because the demo uploads a document and types
a sentence in the same turn.

## A note on the mandated models

The assignment specifies Groq with `gemma2-9b-it`, and `llama-3.3-70b-versatile` for
context. **Groq has decommissioned both.** Its API returns:

```
Error code: 400 - The model `gemma2-9b-it` has been decommissioned and is no longer
supported. model_decommissioned
```

OpenRouter still serves the mandated reasoning model exactly, and the current release
of the mandated Gemma family for extraction, so it is the default provider:

| Role | Assignment asked for | Running |
|---|---|---|
| Extraction | `gemma2-9b-it` | `google/gemma-4-31b-it` — same family, current release |
| Reasoning | `llama-3.3-70b-versatile` | `meta-llama/llama-3.3-70b-instruct` — **the same model** |

Groq is still one env var away, on its own substitutes:

```bash
llm_provider=groq          # -> openai/gpt-oss-20b + openai/gpt-oss-120b
```

Both providers go through a langchain chat model with the same interface — OpenRouter
is OpenAI-API-compatible — so the graph never learns which one it is talking to.
`GET /api/health` reports the provider and models actually in use.

### Two things measurement changed

**`google/gemma-3-12b-it` was the first pick, and it silently broke the edit tool.**
Asked for a patch it returned `{"Affected Quantity": "48 capsules", "batch_number": ...}`
— the *label* for one field, the key for the other. The merge loop reads field keys, so
the quantity was dropped and the form just looked incomplete. Nothing errored. The fix
was both parts: move to `gemma-4-31b-it`, which returns keys correctly and is 3x faster,
and normalize any casing or spelling of a known field name back onto its key so no
future model can reintroduce it. `test_key_normalization` locks it down.

**OpenRouter's default provider routing was the latency problem.** OpenRouter
load-balances each model across several hosts, and its default pick was consistently a
slow one — the risk node measured 15.7s median. Adding `provider: {"sort": "latency"}`
took it to 4.5s. End to end a correction went from 45s to under 5s.

| Turn | Before | After |
|---|---|---|
| Edit complaint | 45.6s | **4.8s** |
| PDF extraction | 58.0s | **8.7s** |
| Ask a question | — | **2.2s** |

## Stack

React 18 + Redux Toolkit · FastAPI · LangGraph · OpenRouter / Groq · SQLAlchemy
(Postgres / SQLite) · Vite · Inter

Redux holds the complaint form, the risk assessment, the chat thread and the theme.
The form is a pure function of store state, so "the AI fills the form" is one reducer
writing `state.form` — not imperative DOM updates from a chat callback.

## Tests

```bash
python backend/test_agent.py
```

Covers JSON salvage from chatty model output, the patch merge that must never drop a
field, the completeness gate, and duplicate scoring. No network, no framework.
