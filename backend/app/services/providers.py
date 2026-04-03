"""AI provider abstraction for multi-provider analysis.

Each provider takes the same prompt and returns the same JSON structure.
"""

import json
import re

import anthropic
import openai
from google import genai

from app.core.database import get_sync_db
from app.core.encryption import decrypt


# ── Model registry ───────────────────────────────────────────────────────────

MODELS = {
    # Anthropic
    "claude-sonnet": {"provider": "anthropic", "model_id": "claude-sonnet-4-20250514", "label": "Claude Sonnet"},
    "claude-haiku": {"provider": "anthropic", "model_id": "claude-haiku-4-5-20251001", "label": "Claude Haiku"},
    "claude-opus": {"provider": "anthropic", "model_id": "claude-opus-4-20250514", "label": "Claude Opus"},
    # OpenAI
    "gpt-4o": {"provider": "openai", "model_id": "gpt-4o", "label": "GPT-4o"},
    "gpt-4o-mini": {"provider": "openai", "model_id": "gpt-4o-mini", "label": "GPT-4o Mini"},
    # Google
    "gemini-2.0-flash": {"provider": "google", "model_id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash"},
    "gemini-2.5-pro": {"provider": "google", "model_id": "gemini-2.5-pro-preview-05-06", "label": "Gemini 2.5 Pro"},
}


def get_available_models() -> list[dict]:
    """Return model registry for the frontend."""
    return [
        {"key": key, "provider": m["provider"], "label": m["label"]}
        for key, m in MODELS.items()
    ]


# ── Key resolution ───────────────────────────────────────────────────────────

def _get_user_key(user_id: str, provider: str) -> str:
    """Get decrypted API key for a provider from the user's stored keys."""
    db = get_sync_db()
    doc = db.users.find_one({"_id": user_id}, {"api_keys": 1, "encrypted_api_key": 1})
    if not doc:
        raise RuntimeError(f"User not found")

    # Try new multi-key store first
    api_keys = doc.get("api_keys", {})
    if provider in api_keys:
        return decrypt(api_keys[provider])

    # Fall back to legacy single key for anthropic
    if provider == "anthropic" and doc.get("encrypted_api_key"):
        return decrypt(doc["encrypted_api_key"])

    raise RuntimeError(f"No {provider} API key found. Add one in settings.")


# ── Provider calls ───────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text.strip())


def call_anthropic(user_id: str, model_id: str, prompt: str) -> dict:
    key = _get_user_key(user_id, "anthropic")
    client = anthropic.Anthropic(api_key=key)
    message = client.messages.create(
        model=model_id,
        max_tokens=2048,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json(message.content[0].text)


def call_openai(user_id: str, model_id: str, prompt: str) -> dict:
    key = _get_user_key(user_id, "openai")
    client = openai.OpenAI(api_key=key)
    response = client.chat.completions.create(
        model=model_id,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json(response.choices[0].message.content or "")


def call_google(user_id: str, model_id: str, prompt: str) -> dict:
    key = _get_user_key(user_id, "google")
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model=model_id,
        contents=prompt,
        config={"temperature": 0},
    )
    return _parse_json(response.text)


PROVIDER_CALLERS = {
    "anthropic": call_anthropic,
    "openai": call_openai,
    "google": call_google,
}


def call_model(user_id: str, model_key: str, prompt: str) -> dict:
    """Call any model by its registry key. Returns parsed JSON dict."""
    spec = MODELS.get(model_key)
    if not spec:
        raise ValueError(f"Unknown model: {model_key}")

    caller = PROVIDER_CALLERS[spec["provider"]]
    return caller(user_id, spec["model_id"], prompt)
