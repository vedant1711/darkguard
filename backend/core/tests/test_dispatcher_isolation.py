"""Tests for dispatcher isolation and payload key validation."""

from __future__ import annotations

import asyncio
import logging

import pytest

from core.dispatcher import dispatch
from core.interfaces import BaseAnalyzer
from core.models import Detection
from core.registry import AnalyzerRegistry


class _MockAnalyzer(BaseAnalyzer):
    """Analyzer that records whether it was called."""

    def __init__(
        self,
        analyzer_name: str,
        keys: list[str],
        detections: list[Detection] | None = None,
    ) -> None:
        self._name = analyzer_name
        self._keys = keys
        self._detections = detections or []
        self.was_called = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def required_payload_keys(self) -> list[str]:
        return self._keys

    async def analyze(self, payload: dict[str, object]) -> list[Detection]:
        self.was_called = True
        return self._detections


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    AnalyzerRegistry.clear()


def _run(coro: object) -> list[Detection]:
    return asyncio.run(coro)  # type: ignore[arg-type]


class TestDispatcherIsolation:
    """Test that the dispatcher respects required_payload_keys."""

    def test_skips_analyzer_with_missing_keys(self) -> None:
        analyzer = _MockAnalyzer("needs_data", ["missing_key"])
        payload: dict[str, object] = {"some_other_key": "value"}

        results = _run(dispatch(payload, analyzers={"needs_data": analyzer}))
        assert results == []
        assert not analyzer.was_called

    def test_runs_analyzer_with_present_keys(self) -> None:
        det = Detection(
            category="test",
            element_selector="#el",
            confidence=0.9,
            explanation="test",
            severity="medium",
        )
        analyzer = _MockAnalyzer("has_data", ["dom_metadata"], [det])
        payload: dict[str, object] = {"dom_metadata": {"elements": []}}

        results = _run(dispatch(payload, analyzers={"has_data": analyzer}))
        assert len(results) == 1
        assert analyzer.was_called

    def test_stamps_analyzer_name(self) -> None:
        det = Detection(
            category="test",
            element_selector="#el",
            confidence=0.9,
            explanation="test",
            severity="medium",
        )
        analyzer = _MockAnalyzer("stamper", ["key"], [det])
        payload: dict[str, object] = {"key": "value"}

        results = _run(dispatch(payload, analyzers={"stamper": analyzer}))
        assert results[0].analyzer_name == "stamper"

    def test_corroboration_requires_different_analyzers(self) -> None:
        det1 = Detection(
            category="visual_interference",
            element_selector="#btn",
            confidence=0.8,
            explanation="test1",
            severity="medium",
            analyzer_name="a1",
        )
        det2 = Detection(
            category="visual_interference",
            element_selector="#btn",
            confidence=0.7,
            explanation="test2",
            severity="medium",
            analyzer_name="a2",
        )
        a1 = _MockAnalyzer("a1", ["key"], [det1])
        a2 = _MockAnalyzer("a2", ["key"], [det2])
        payload: dict[str, object] = {"key": "value"}

        results = _run(dispatch(payload, analyzers={"a1": a1, "a2": a2}))
        # Should keep highest confidence and be corroborated
        assert len(results) == 1
        assert results[0].corroborated is True

    def test_logs_warning_for_missing_keys(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        analyzer = _MockAnalyzer("warned", ["nonexistent"])
        payload: dict[str, object] = {}

        with caplog.at_level(logging.WARNING, logger="core.dispatcher"):
            _run(dispatch(payload, analyzers={"warned": analyzer}))
        assert "Skipping analyzer warned" in caplog.text
