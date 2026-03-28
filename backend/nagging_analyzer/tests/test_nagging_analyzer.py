"""Tests for the Nagging Analyzer."""

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
    from nagging_analyzer.service import NaggingAnalyzerService
    return NaggingAnalyzerService()


def _run(coro: object) -> list[Detection]:
    return asyncio.run(coro)  # type: ignore[arg-type]


class TestNaggingAnalyzer:
    """Unit tests for NaggingAnalyzerService."""

    def test_analyzer_name_property(self, service: object) -> None:
        assert service.name == "nagging"  # type: ignore[attr-defined]

    def test_required_payload_keys(self, service: object) -> None:
        assert service.required_payload_keys == ["nagging_events"]  # type: ignore[attr-defined]

    def test_detects_notification_inflation(self, service: object) -> None:
        payload = {
            "nagging_events": {
                "events": [
                    {"type": "notification_prompt", "text": "Allow notifications?"},
                    {"type": "notification_prompt", "text": "Are you sure?"},
                ]
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        
        assert len(results) == 1
        assert results[0].category == "notification_inflation"
        assert "GDPR-Art7" in results[0].regulation_refs

    def test_detects_persistent_modals(self, service: object) -> None:
        payload = {
            "nagging_events": {
                "events": [
                    {"type": "app_install_prompt", "text": "Get the app!"},
                    {"type": "modal", "text": "Sign up for newsletter"},
                    {"type": "modal", "text": "Special offer!"},
                ]
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        
        assert len(results) == 1
        assert results[0].category == "persistent_nagging"
        assert "3 interruptive popups" in results[0].explanation

    def test_detects_persistent_overlay(self, service: object) -> None:
        payload = {
            "nagging_events": {
                "has_persistent_overlay": True,
                "events": []
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        
        assert len(results) == 1
        assert results[0].category == "persistent_nagging"
        assert results[0].element_selector == "overlay"

    def test_ignores_clean_session(self, service: object) -> None:
        payload = {
            "nagging_events": {
                "has_persistent_overlay": False,
                "events": [
                    {"type": "modal", "text": "Welcome popup"}
                ]
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        
        assert len(results) == 0
