"""Runtime config. Walks up the tree for a .env so the repo works whether the
keys live beside the app or in the parent project folder."""
import os
from pathlib import Path

from dotenv import load_dotenv

for _parent in Path(__file__).resolve().parents:
    _f = _parent / ".env"
    if _f.exists():
        load_dotenv(_f, override=False)


def env(name: str, default: str | None = None) -> str | None:
    """Keys in the provided .env are lowercase; tolerate either casing."""
    return os.getenv(name) or os.getenv(name.upper()) or os.getenv(name.lower()) or default


GROQ_API_KEY = env("groq_api_key")
OPENROUTER_API_KEY = env("openrouter_api_key")

# The assignment mandates Groq with gemma2-9b-it (fast extraction) and
# llama-3.3-70b-versatile (reasoning). Groq decommissioned BOTH -- its API returns
# `model_decommissioned` for each. OpenRouter still serves the mandated reasoning
# model exactly, and the current Gemma release for the extraction role, so it is the
# default provider. Set llm_provider=groq to run on Groq's substitutes instead.
LLM_PROVIDER = (env("llm_provider", "openrouter") or "openrouter").strip().lower()

_DEFAULTS = {
    # provider:    (extraction,               reasoning)
    "openrouter": ("google/gemma-4-31b-it", "meta-llama/llama-3.3-70b-instruct"),
    "groq": ("openai/gpt-oss-20b", "openai/gpt-oss-120b"),
}
_extraction_default, _reasoning_default = _DEFAULTS.get(LLM_PROVIDER, _DEFAULTS["openrouter"])

EXTRACTION_MODEL = env("extraction_model", _extraction_default)
REASONING_MODEL = env("reasoning_model", _reasoning_default)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
APP_TITLE = "AIVOA Complaint Management"   # OpenRouter shows this on the dashboard
APP_URL = "https://aivoa.ai"

# Postgres when DATABASE_URL is set (see docker-compose.yml); SQLite otherwise so
# a reviewer can clone and run with zero infrastructure.
DATABASE_URL = env("database_url", "sqlite:///./aivoa_qms.db")

CORS_ORIGINS = (env("cors_origins", "http://localhost:5173,http://127.0.0.1:5173") or "").split(",")
