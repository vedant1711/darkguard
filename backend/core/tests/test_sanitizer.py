"""Tests for the server-side PII sanitizer."""

from __future__ import annotations

import logging

import pytest

from core.sanitizer import sanitize_payload, sanitize_text


class TestSanitizeText:
    """Unit tests for sanitize_text()."""

    def test_redacts_emails(self) -> None:
        text = "Contact john.doe@example.com for help"
        result = sanitize_text(text)
        assert "[REDACTED]" in result
        assert "john.doe@example.com" not in result

    def test_redacts_phone_numbers(self) -> None:
        text = "Call (555) 123-4567 or +1-800-555-0199"
        result = sanitize_text(text)
        assert "(555) 123-4567" not in result
        assert "[REDACTED]" in result

    def test_redacts_ssns(self) -> None:
        text = "SSN: 123-45-6789"
        result = sanitize_text(text)
        assert "123-45-6789" not in result
        assert "[REDACTED]" in result

    def test_redacts_credit_cards(self) -> None:
        text = "Card: 4111 1111 1111 1111"
        result = sanitize_text(text)
        assert "4111 1111 1111 1111" not in result
        assert "[REDACTED]" in result

    def test_preserves_clean_text(self) -> None:
        text = "This is a perfectly normal button label"
        result = sanitize_text(text)
        assert result == text

    def test_logs_warning_on_pii(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING, logger="core.sanitizer"):
            sanitize_text("Email: test@example.com")
        assert "PII leak detected" in caplog.text

    def test_redacts_multiple_pii_types(self) -> None:
        text = "john@test.com called 555-123-4567 with SSN 123-45-6789"
        result = sanitize_text(text)
        assert "john@test.com" not in result
        assert "555-123-4567" not in result
        assert "123-45-6789" not in result
        assert result.count("[REDACTED]") >= 3


class TestSanitizePayload:
    """Unit tests for sanitize_payload()."""

    def test_sanitizes_nested_strings(self) -> None:
        payload = {
            "text_content": {
                "body_text": "Contact user@test.com for details",
                "button_labels": [
                    {"selector": "#btn", "text": "No thanks"}
                ],
            }
        }
        result = sanitize_payload(payload)
        assert "user@test.com" not in str(result)
        assert "[REDACTED]" in str(result)
        # Original should be unchanged
        assert "user@test.com" in str(payload)

    def test_does_not_modify_original(self) -> None:
        payload = {"text": "email@example.com"}
        original = payload.copy()
        sanitize_payload(payload)
        assert payload == original

    def test_handles_empty_payload(self) -> None:
        result = sanitize_payload({})
        assert result == {}

    def test_preserves_non_string_values(self) -> None:
        payload = {"count": 42, "enabled": True, "ratio": 0.5}
        result = sanitize_payload(payload)
        assert result == payload
