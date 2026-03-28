"""Tests for the Pricing Analyzer."""

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
    from pricing_analyzer.service import PricingAnalyzerService
    return PricingAnalyzerService()


def _run(coro: object) -> list[Detection]:
    return asyncio.run(coro)  # type: ignore[arg-type]


class TestPricingAnalyzer:
    """Unit tests for PricingAnalyzerService."""

    def test_analyzer_name_property(self, service: object) -> None:
        assert service.name == "pricing"  # type: ignore[attr-defined]

    def test_required_payload_keys(self, service: object) -> None:
        assert service.required_payload_keys == ["text_content"]  # type: ignore[attr-defined]

    @patch("pricing_analyzer.service.get_llm_client")
    def test_detects_bnpl_deception(self, mock_get_llm: object, service: object) -> None:
        mock_llm = AsyncMock()
        mock_get_llm.return_value = mock_llm  # type: ignore[attr-defined]
        
        # Mock the LLM to return a BNPL detection
        mock_llm.generate.return_value = json.dumps([
            {
                "category": "bnpl_deception",
                "confidence": 0.85,
                "explanation": "Buy Now Pay Later option hides the massive 35% interest rate."
            }
        ])

        payload = {
            "text_content": {
                "body_text": "Buy this TV now for just $50/month! *Standard APR applies."
            }
        }
        
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        
        assert len(results) == 1
        assert results[0].category == "bnpl_deception"
        assert results[0].analyzer_name == "pricing"
        assert "TILA" in results[0].regulation_refs
        
        # Verify LLM was called with the purpose
        mock_get_llm.assert_called_with(purpose="text_classification")  # type: ignore[attr-defined]

    @patch("pricing_analyzer.service.get_llm_client")
    def test_detects_intermediate_currency(self, mock_get_llm: object, service: object) -> None:
        mock_llm = AsyncMock()
        mock_get_llm.return_value = mock_llm  # type: ignore[attr-defined]
        
        mock_llm.generate.return_value = json.dumps([
            {
                "category": "intermediate_currency",
                "confidence": 0.9,
                "explanation": "Uses 'Gems' to hide the real $30 cost."
            }
        ])

        payload = {
            "text_content": {
                "body_text": "Unlock this skin for 500 Gems! Buy 600 Gems for $4.99."
            }
        }
        
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert len(results) == 1
        assert results[0].category == "intermediate_currency"
        assert "DSA-Art25" in results[0].regulation_refs

    @patch("pricing_analyzer.service.get_llm_client")
    def test_returns_empty_on_clean_text(self, mock_get_llm: object, service: object) -> None:
        mock_llm = AsyncMock()
        mock_get_llm.return_value = mock_llm  # type: ignore[attr-defined]
        
        mock_llm.generate.return_value = "[]"

        payload = {
            "text_content": {
                "body_text": "Buy this shoe for $50.00 total. No hidden fees."
            }
        }
        
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert len(results) == 0

    def test_returns_empty_on_missing_text(self, service: object) -> None:
        payload: dict[str, object] = {"url": "https://example.com"}
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert len(results) == 0
