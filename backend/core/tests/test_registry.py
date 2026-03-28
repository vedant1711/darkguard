"""Tests for the AnalyzerRegistry."""

from __future__ import annotations

import asyncio

import pytest

from core.interfaces import BaseAnalyzer
from core.models import Detection
from core.registry import AnalyzerRegistry


class _DummyAnalyzer(BaseAnalyzer):
    """Minimal analyzer for registry tests."""

    def __init__(self, analyzer_name: str = "dummy") -> None:
        self._name = analyzer_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def required_payload_keys(self) -> list[str]:
        return ["test_data"]

    async def analyze(self, payload: dict[str, object]) -> list[Detection]:
        return []


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    """Ensure a clean registry for each test."""
    AnalyzerRegistry.clear()


class TestAnalyzerRegistry:
    """Unit tests for AnalyzerRegistry."""

    def test_register_and_get_all(self) -> None:
        analyzer = _DummyAnalyzer("test1")
        AnalyzerRegistry.register(analyzer)
        all_analyzers = AnalyzerRegistry.get_all()
        assert "test1" in all_analyzers
        assert all_analyzers["test1"] is analyzer

    def test_duplicate_registration_raises(self) -> None:
        AnalyzerRegistry.register(_DummyAnalyzer("dup"))
        with pytest.raises(ValueError, match="already registered"):
            AnalyzerRegistry.register(_DummyAnalyzer("dup"))

    def test_get_by_name(self) -> None:
        analyzer = _DummyAnalyzer("findme")
        AnalyzerRegistry.register(analyzer)
        assert AnalyzerRegistry.get("findme") is analyzer
        assert AnalyzerRegistry.get("nonexistent") is None

    def test_clear(self) -> None:
        AnalyzerRegistry.register(_DummyAnalyzer("clearme"))
        assert len(AnalyzerRegistry.get_all()) == 1
        AnalyzerRegistry.clear()
        assert len(AnalyzerRegistry.get_all()) == 0

    def test_discover_imports_analyzer_packages(self) -> None:
        """discover() should import *_analyzer packages and register them."""
        AnalyzerRegistry.discover()
        all_analyzers = AnalyzerRegistry.get_all()
        # At minimum, the 4 built-in analyzers should be discovered
        assert len(all_analyzers) >= 4
        assert "dom" in all_analyzers
        assert "text" in all_analyzers
        assert "visual" in all_analyzers
        assert "review" in all_analyzers
