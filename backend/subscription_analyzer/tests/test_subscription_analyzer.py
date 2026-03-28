"""Tests for the Subscription Analyzer."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from core.models import Detection
from core.registry import AnalyzerRegistry


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    AnalyzerRegistry.clear()


@pytest.fixture
def service() -> object:
    from subscription_analyzer.service import SubscriptionAnalyzerService
    return SubscriptionAnalyzerService()


def _run(coro: object) -> list[Detection]:
    return asyncio.run(coro)  # type: ignore[arg-type]


class TestSubscriptionAnalyzer:
    """Unit tests for SubscriptionAnalyzerService."""

    def test_analyzer_name_property(self, service: object) -> None:
        assert service.name == "subscription"  # type: ignore[attr-defined]

    def test_required_payload_keys(self, service: object) -> None:
        assert service.required_payload_keys == ["text_content"]  # type: ignore[attr-defined]

    @patch("subscription_analyzer.service.get_llm_client")
    def test_detects_roach_motel(self, mock_get_llm: object, service: object) -> None:
        mock_llm = AsyncMock()
        mock_get_llm.return_value = mock_llm  # type: ignore[attr-defined]
        
        # Mock the LLM to return a roach motel detection
        mock_llm.generate.return_value = json.dumps([
            {
                "category": "roach_motel",
                "confidence": 0.9,
                "explanation": "To cancel your subscription, you must call our hotline between 9am and 5pm EST."
            }
        ])

        payload = {
            "text_content": {
                "body_text": "To cancel your subscription, you must call our hotline between 9am and 5pm EST.",
                "button_labels": ["Cancel Subscription"]
            }
        }
        
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        
        assert len(results) == 1
        assert results[0].category == "roach_motel"
        assert results[0].analyzer_name == "subscription"
        assert "FTC-NegativeOption" in results[0].regulation_refs
        
        # Verify LLM was called with the purpose
        mock_get_llm.assert_called_with(purpose="text_classification")  # type: ignore[attr-defined]

    @patch("subscription_analyzer.service.get_llm_client")
    def test_returns_empty_on_clean_text(self, mock_get_llm: object, service: object) -> None:
        mock_llm = AsyncMock()
        mock_get_llm.return_value = mock_llm  # type: ignore[attr-defined]
        
        mock_llm.generate.return_value = "[]"

        payload = {
            "text_content": {
                "body_text": "You can easily cancel your subscription anytime by clicking the button below.",
                "button_labels": ["Cancel Anytime"]
            }
        }
        
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert len(results) == 0

    def test_returns_empty_on_missing_text(self, service: object) -> None:
        # Should gracefully return empty list without calling LLM
        payload: dict[str, object] = {"url": "https://example.com"}
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert len(results) == 0
