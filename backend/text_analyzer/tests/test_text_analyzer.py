"""Tests for the Text Analyzer."""

from __future__ import annotations

import asyncio

import pytest

from core.models import Detection
from core.registry import AnalyzerRegistry


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    AnalyzerRegistry.clear()


@pytest.fixture
def service() -> object:
    from text_analyzer.service import TextAnalyzerService
    return TextAnalyzerService()


def _run(coro: object) -> list[Detection]:
    return asyncio.run(coro)  # type: ignore[arg-type]


class TestTextAnalyzer:
    """Unit tests for TextAnalyzerService."""

    def test_analyzer_name_property(self, service: object) -> None:
        assert service.name == "text"  # type: ignore[attr-defined]

    def test_required_payload_keys(self, service: object) -> None:
        assert service.required_payload_keys == ["text_content"]  # type: ignore[attr-defined]

    def test_detects_confirmshaming(self, service: object) -> None:
        payload = {
            "text_content": {
                "button_labels": [
                    {"selector": "#decline", "text": "No thanks, I'd rather pay full price"},
                ],
                "headings": [],
                "body_text": "",
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert any(d.category == "confirmshaming" for d in results)
        cs = [d for d in results if d.category == "confirmshaming"][0]
        assert cs.analyzer_name == "text"
        assert cs.platform_context == "ecommerce"
        assert "FTC-S5" in cs.regulation_refs

    def test_detects_urgency_scarcity(self, service: object) -> None:
        payload = {
            "text_content": {
                "button_labels": [],
                "headings": [],
                "body_text": "Hurry! Only 3 left in stock. 47 people are viewing this item.",
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        urgency = [d for d in results if d.category == "urgency_scarcity"]
        assert len(urgency) >= 1
        assert urgency[0].analyzer_name == "text"

    def test_detects_misdirection(self, service: object) -> None:
        payload = {
            "text_content": {
                "button_labels": [
                    {"selector": "#cta", "text": "Claim"},
                ],
                "headings": [],
                "body_text": "",
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        mis = [d for d in results if d.category == "misdirection"]
        assert len(mis) >= 1
        assert mis[0].analyzer_name == "text"

    def test_returns_empty_on_clean_text(self, service: object) -> None:
        payload = {
            "text_content": {
                "button_labels": [
                    {"selector": "#ok", "text": "Submit"},
                ],
                "headings": [],
                "body_text": "Welcome to our website.",
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert results == []
