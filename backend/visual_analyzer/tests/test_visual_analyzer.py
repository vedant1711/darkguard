"""Tests for the Visual Analyzer."""

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
    from visual_analyzer.service import VisualAnalyzerService
    return VisualAnalyzerService()


def _run(coro: object) -> list[Detection]:
    return asyncio.run(coro)  # type: ignore[arg-type]


class TestVisualAnalyzer:
    """Unit tests for VisualAnalyzerService."""

    def test_analyzer_name_property(self, service: object) -> None:
        assert service.name == "visual"  # type: ignore[attr-defined]

    def test_required_payload_keys(self, service: object) -> None:
        assert service.required_payload_keys == ["dom_metadata"]  # type: ignore[attr-defined]

    def test_returns_empty_on_missing_metadata(self, service: object) -> None:
        payload: dict[str, object] = {"dom_metadata": {}}
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert results == []

    def test_returns_empty_on_non_dict_metadata(self, service: object) -> None:
        payload: dict[str, object] = {"dom_metadata": "invalid"}
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert results == []
