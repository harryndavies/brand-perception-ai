"""Shared utility functions."""

import json
import re


def parse_json_response(raw: str) -> dict:
    """Parse JSON from an AI provider response, stripping markdown fences if present."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text.strip())
