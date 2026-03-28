"""Tests for the Privacy Analyzer."""

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
    from privacy_analyzer.service import PrivacyAnalyzerService
    return PrivacyAnalyzerService()


def _run(coro: object) -> list[Detection]:
    return asyncio.run(coro)  # type: ignore[arg-type]


class TestPrivacyAnalyzer:
    """Unit tests for PrivacyAnalyzerService."""

    def test_analyzer_name_property(self, service: object) -> None:
        assert service.name == "privacy"  # type: ignore[attr-defined]

    def test_required_payload_keys(self, service: object) -> None:
        assert service.required_payload_keys == ["dom_metadata"]  # type: ignore[attr-defined]

    def test_detects_zuckering_share_third_party(self, service: object) -> None:
        payload = {
            "dom_metadata": {
                "prechecked_inputs": [
                    {
                        "tag_name": "input",
                        "selector": "#share",
                        "text_content": "Share my profile with third party partners",
                        "attributes": {"type": "checkbox", "checked": ""},
                    }
                ]
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        
        assert len(results) == 1
        assert results[0].category == "privacy_zuckering"
        assert "GDPR-Art25" in results[0].regulation_refs

    def test_ignores_unchecked_invasive_settings(self, service: object) -> None:
        # If it's not in prechecked_inputs, the user has to explicitly check it, which is legal
        payload = {
            "dom_metadata": {
                "interactive_elements": [
                    {
                        "tag_name": "input",
                        "selector": "#share",
                        "text_content": "Make my profile public",
                        "attributes": {"type": "checkbox"}
                    }
                ]
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert len(results) == 0

    def test_ignores_negated_prechecked_settings(self, service: object) -> None:
        # "Do not share" being prechecked is good privacy!
        payload = {
            "dom_metadata": {
                "prechecked_inputs": [
                    {
                        "tag_name": "input",
                        "selector": "#noshare",
                        "text_content": "Do not share my information with third parties",
                        "attributes": {"type": "checkbox", "checked": ""},
                    }
                ]
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert len(results) == 0
