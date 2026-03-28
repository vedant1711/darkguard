"""Tests for the Review Analyzer."""

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
    from review_analyzer.service import ReviewAnalyzerService
    return ReviewAnalyzerService()


def _run(coro: object) -> list[Detection]:
    return asyncio.run(coro)  # type: ignore[arg-type]


class TestReviewAnalyzer:
    """Unit tests for ReviewAnalyzerService."""

    def test_analyzer_name_property(self, service: object) -> None:
        assert service.name == "review"  # type: ignore[attr-defined]

    def test_required_payload_keys(self, service: object) -> None:
        assert service.required_payload_keys == ["review_text"]  # type: ignore[attr-defined]

    def test_detects_generic_praise(self, service: object) -> None:
        reviews = " --- ".join([
            "Amazing product! Highly recommend!",
            "Great product, five stars!",
            "Excellent product! Must buy!",
            "Amazing item, exceeded expectations!",
        ])
        payload: dict[str, object] = {
            "review_text": reviews,
            "url": "https://example.com",
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert any(d.category == "fake_social_proof" for d in results)
        fsp = [d for d in results if d.category == "fake_social_proof"][0]
        assert fsp.analyzer_name == "review"
        assert fsp.platform_context == "ecommerce"
        assert "FTC-S5" in fsp.regulation_refs

    def test_returns_empty_on_short_text(self, service: object) -> None:
        payload: dict[str, object] = {
            "review_text": "Good",
            "url": "https://example.com",
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert results == []

    def test_returns_empty_on_missing_review(self, service: object) -> None:
        payload: dict[str, object] = {"url": "https://example.com"}
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert results == []
