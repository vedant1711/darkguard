"""
core/sanitizer.py — Server-side PII sanitizer (defense-in-depth).

Actively re-redacts PII from payloads that should already be sanitized by
the browser-side ``sanitizer.ts``.  This is the second layer of protection,
plus a pre-LLM layer for analyzers that call external APIs.

Three-layer architecture:
  Layer 1 — Browser (sanitizer.ts)
  Layer 2 — Server (this module, called by views.py before dispatch)
  Layer 3 — Pre-LLM (sanitize_text() called by each LLM-using analyzer)
"""

from __future__ import annotations

import copy
import logging
import re

logger = logging.getLogger(__name__)

PII_REPLACEMENT = "[REDACTED]"

# ── PII regex patterns (mirrors extension/src/content/sanitizer.ts) ───

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)
PHONE_RE = re.compile(
    r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
)
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_RE = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")

_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", EMAIL_RE),
    ("phone", PHONE_RE),
    ("ssn", SSN_RE),
    ("credit_card", CREDIT_CARD_RE),
]


def sanitize_text(text: str) -> str:
    """Actively redact PII from a text string.

    Logs a warning if any PII is found (it should have been caught
    by the browser-side sanitizer already).

    Returns:
        The text with all matched PII replaced by ``[REDACTED]``.
    """
    sanitized = text
    for pii_type, pattern in _PII_PATTERNS:
        match = pattern.search(sanitized)
        if match:
            logger.warning(
                "PII leak detected server-side (%s): browser sanitizer may "
                "have missed this. Redacting.",
                pii_type,
            )
            sanitized = pattern.sub(PII_REPLACEMENT, sanitized)
    return sanitized


def _sanitize_value(value: object) -> object:
    """Recursively sanitize a value (str, list, or dict)."""
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    return value


def sanitize_payload(payload: dict[str, object]) -> dict[str, object]:
    """Deep-walk the entire payload and redact PII from all string values.

    This operates on a deep copy so the original payload is not mutated.

    Args:
        payload: The validated request payload.

    Returns:
        A sanitized copy of the payload.
    """
    return _sanitize_value(copy.deepcopy(payload))  # type: ignore[return-value]
