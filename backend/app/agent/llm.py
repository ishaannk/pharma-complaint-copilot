"""Model handles + a JSON call that survives chatty models.

OpenRouter is OpenAI-API-compatible, so both providers go through a langchain chat
model with the same interface -- no adapter layer, and the graph never learns which
provider it is talking to.
"""
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import (
    APP_TITLE,
    APP_URL,
    EXTRACTION_MODEL,
    GROQ_API_KEY,
    LLM_PROVIDER,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    REASONING_MODEL,
)


def _model(name: str, temperature: float):
    if LLM_PROVIDER == "groq":
        if not GROQ_API_KEY:
            raise RuntimeError("groq_api_key missing. Add it to .env, or set llm_provider=openrouter.")
        from langchain_groq import ChatGroq

        return ChatGroq(model=name, api_key=GROQ_API_KEY, temperature=temperature, max_retries=2)

    if not OPENROUTER_API_KEY:
        raise RuntimeError("openrouter_api_key missing. Add it to .env, or set llm_provider=groq.")
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=name,
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        temperature=temperature,
        timeout=90,
        max_retries=2,
        # OpenRouter attributes usage to the app on its dashboard.
        default_headers={"HTTP-Referer": APP_URL, "X-Title": APP_TITLE},
        # OpenRouter load-balances across several hosts per model, and its default
        # pick is often a slow one: the risk node measured 15.7s median by default
        # versus 4.5s sorted by latency. A QA reviewer is waiting on this turn.
        extra_body={"provider": {"sort": "latency"}},
    )


extractor = _model(EXTRACTION_MODEL, 0.0)   # deterministic field extraction
reasoner = _model(REASONING_MODEL, 0.3)     # risk / root-cause / CAPA reasoning

# ChatGroq exposes .model_name, ChatOpenAI .model_name too -- but keep the configured
# id around so the trace shows what was asked for, not what the client renamed it to.
EXTRACTOR_ID = EXTRACTION_MODEL
REASONER_ID = REASONING_MODEL


_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.S)


def _first_json_object(text: str) -> str:
    """Slice out the outermost {...} so prose around the JSON doesn't break us."""
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object in model output")
    depth, in_str, esc = 0, False, False
    for i, ch in enumerate(text[start:], start):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("unterminated JSON object")


def json_call(model, system: str, user: str) -> dict:
    """Ask for JSON and parse it. Groq's json_object mode is the happy path;
    the brace-scanner is the fallback for models that wrap output in prose."""
    messages = [SystemMessage(content=system), HumanMessage(content=user)]
    try:
        raw = model.bind(response_format={"type": "json_object"}).invoke(messages).content
    except Exception:
        raw = model.invoke(messages).content

    if isinstance(raw, list):  # some providers return content blocks
        raw = "".join(p.get("text", "") for p in raw if isinstance(p, dict))

    for candidate in (raw, *(m.group(1) for m in _FENCE.finditer(raw))):
        try:
            return json.loads(candidate)
        except Exception:
            pass
    return json.loads(_first_json_object(raw))


def text_call(model, system: str, user: str) -> str:
    return model.invoke([SystemMessage(content=system), HumanMessage(content=user)]).content.strip()
