"""AI provider abstraction for multi-provider analysis.

Each provider takes the same prompt and returns the same JSON structure.
"""

import json
import logging

import anthropic
import openai
from google import genai

from app.core.database import get_sync_db
from app.core.encryption import decrypt
from app.core.enums import Provider
from app.core.utils import parse_json_response

logger = logging.getLogger(__name__)

_TIMEOUT = 120.0  # seconds


class ProviderError(Exception):
    """Raised when an AI provider API call fails."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"{provider}: {message}")


# -- Model registry -----------------------------------------------------------

MODELS = {
    # Anthropic
    "claude-sonnet": {"provider": Provider.ANTHROPIC, "model_id": "claude-sonnet-4-20250514", "label": "Claude Sonnet"},
    "claude-haiku": {"provider": Provider.ANTHROPIC, "model_id": "claude-haiku-4-5-20251001", "label": "Claude Haiku"},
    "claude-opus": {"provider": Provider.ANTHROPIC, "model_id": "claude-opus-4-20250514", "label": "Claude Opus"},
    # OpenAI
    "gpt-4o": {"provider": Provider.OPENAI, "model_id": "gpt-4o", "label": "GPT-4o"},
    "gpt-4o-mini": {"provider": Provider.OPENAI, "model_id": "gpt-4o-mini", "label": "GPT-4o Mini"},
    # Google
    "gemini-2.0-flash": {"provider": Provider.GOOGLE, "model_id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash"},
    "gemini-2.5-pro": {"provider": Provider.GOOGLE, "model_id": "gemini-2.5-pro-preview-05-06", "label": "Gemini 2.5 Pro"},
}


def get_available_models() -> list[dict]:
    """Return model registry for the frontend."""
    return [
        {"key": key, "provider": m["provider"], "label": m["label"]}
        for key, m in MODELS.items()
    ]


# -- Key resolution ------------------------------------------------------------

def _get_user_key(user_id: str, provider: str) -> str:
    """Get decrypted API key for a provider from the user's stored keys."""
    db = get_sync_db()
    doc = db.users.find_one({"_id": user_id}, {"api_keys": 1, "encrypted_api_key": 1})
    if not doc:
        raise ProviderError(provider, "User not found")

    # Try new multi-key store first
    api_keys = doc.get("api_keys", {})
    if provider in api_keys:
        return decrypt(api_keys[provider])

    # Fall back to legacy single key for anthropic
    if provider == Provider.ANTHROPIC and doc.get("encrypted_api_key"):
        return decrypt(doc["encrypted_api_key"])

    raise ProviderError(provider, f"No {provider} API key found. Add one in settings.")


# -- Provider calls ------------------------------------------------------------

def call_anthropic(user_id: str, model_id: str, prompt: str) -> dict:
    key = _get_user_key(user_id, Provider.ANTHROPIC)
    client = anthropic.Anthropic(api_key=key, timeout=_TIMEOUT)
    try:
        message = client.messages.create(
            model=model_id,
            max_tokens=2048,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return parse_json_response(message.content[0].text)
    except anthropic.APIError as exc:
        logger.error("Anthropic API error for model %s: %s", model_id, exc)
        raise ProviderError(Provider.ANTHROPIC, str(exc)) from exc
    except (IndexError, AttributeError) as exc:
        logger.error("Unexpected Anthropic response structure for model %s", model_id)
        raise ProviderError(Provider.ANTHROPIC, "Unexpected response structure") from exc
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON from Anthropic model %s", model_id)
        raise ProviderError(Provider.ANTHROPIC, f"Invalid JSON in response: {exc}") from exc


def call_openai(user_id: str, model_id: str, prompt: str) -> dict:
    key = _get_user_key(user_id, Provider.OPENAI)
    client = openai.OpenAI(api_key=key, timeout=_TIMEOUT)
    try:
        response = client.chat.completions.create(
            model=model_id,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return parse_json_response(response.choices[0].message.content or "")
    except openai.APIError as exc:
        logger.error("OpenAI API error for model %s: %s", model_id, exc)
        raise ProviderError(Provider.OPENAI, str(exc)) from exc
    except (IndexError, AttributeError) as exc:
        logger.error("Unexpected OpenAI response structure for model %s", model_id)
        raise ProviderError(Provider.OPENAI, "Unexpected response structure") from exc
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON from OpenAI model %s", model_id)
        raise ProviderError(Provider.OPENAI, f"Invalid JSON in response: {exc}") from exc


def call_google(user_id: str, model_id: str, prompt: str) -> dict:
    key = _get_user_key(user_id, Provider.GOOGLE)
    client = genai.Client(api_key=key)
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config={"temperature": 0, "http_options": {"timeout": _TIMEOUT * 1000}},
        )
        return parse_json_response(response.text)
    except (AttributeError, TypeError) as exc:
        logger.error("Unexpected Google response structure for model %s", model_id)
        raise ProviderError(Provider.GOOGLE, "Unexpected response structure") from exc
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON from Google model %s", model_id)
        raise ProviderError(Provider.GOOGLE, f"Invalid JSON in response: {exc}") from exc


PROVIDER_CALLERS = {
    Provider.ANTHROPIC: call_anthropic,
    Provider.OPENAI: call_openai,
    Provider.GOOGLE: call_google,
}


def call_model(user_id: str, model_key: str, prompt: str) -> dict:
    """Call any model by its registry key. Returns parsed JSON dict."""
    spec = MODELS.get(model_key)
    if not spec:
        raise ValueError(f"Unknown model: {model_key}")

    caller = PROVIDER_CALLERS[spec["provider"]]
    return caller(user_id, spec["model_id"], prompt)
