"""Tests for the Consent Analyzer."""

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
    from consent_analyzer.service import ConsentAnalyzerService
    return ConsentAnalyzerService()


def _run(coro: object) -> list[Detection]:
    return asyncio.run(coro)  # type: ignore[arg-type]


class TestConsentAnalyzer:
    """Unit tests for ConsentAnalyzerService."""

    def test_analyzer_name_property(self, service: object) -> None:
        assert service.name == "consent"  # type: ignore[attr-defined]

    def test_required_payload_keys(self, service: object) -> None:
        assert service.required_payload_keys == ["dom_metadata"]  # type: ignore[attr-defined]

    def test_detects_missing_reject_button(self, service: object) -> None:
        payload = {
            "dom_metadata": {
                "interactive_elements": [
                    {
                        "tag_name": "button",
                        "text_content": "Accept All Cookies",
                        "selector": "#accept",
                        "attributes": {},
                        "computed_styles": {"background_color": "blue"},
                        "bounding_rect": {"width": 100, "height": 40},
                    },
                    {
                        "tag_name": "button",
                        "text_content": "Manage Settings",
                        "selector": "#manage",
                        "attributes": {},
                        "computed_styles": {"background_color": "white"},
                        "bounding_rect": {"width": 100, "height": 40},
                    },
                ]
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert len(results) == 1
        assert results[0].category == "asymmetric_choice"
        assert "no 1-click 'Reject'" in results[0].explanation
        assert "GDPR-Art7" in results[0].regulation_refs

    def test_detects_smaller_reject_button(self, service: object) -> None:
        payload = {
            "dom_metadata": {
                "interactive_elements": [
                    {
                        "tag_name": "button",
                        "text_content": "Accept",
                        "selector": "#accept",
                        "attributes": {},
                        "computed_styles": {"background_color": "blue"},
                        "bounding_rect": {"width": 200, "height": 50},  # Area 10000
                    },
                    {
                        "tag_name": "a",
                        "text_content": "Decline",
                        "selector": "#decline",
                        "attributes": {},
                        "computed_styles": {"background_color": "transparent"},
                        "bounding_rect": {"width": 50, "height": 20},  # Area 1000
                    },
                ]
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        vi_results = [r for r in results if r.category == "visual_interference"]
        assert len(vi_results) >= 1
        assert "10.0x larger" in vi_results[0].explanation

    def test_detects_prechecked_marketing_cookies(self, service: object) -> None:
        payload = {
            "dom_metadata": {
                "interactive_elements": [
                    {
                        "tag_name": "button",
                        "text_content": "Accept All",
                        "selector": "#accept",
                        "attributes": {},
                        "computed_styles": {},
                        "bounding_rect": {},
                    }
                ],
                "prechecked_inputs": [
                    {
                        "tag_name": "input",
                        "selector": "#marketing",
                        "text_content": "Marketing and Analytics Cookies",
                        "attributes": {"type": "checkbox", "checked": ""},
                        "computed_styles": {},
                        "bounding_rect": {},
                    }
                ]
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        prechecked = [r for r in results if r.category == "prechecked_consent"]
        assert len(prechecked) == 1
        assert "marketing/analytics" in prechecked[0].explanation

    def test_ignores_non_consent_pages(self, service: object) -> None:
        payload = {
            "dom_metadata": {
                "interactive_elements": [
                    {
                        "tag_name": "button",
                        "text_content": "Submit form",
                        "selector": "#submit",
                        "attributes": {},
                        "computed_styles": {},
                        "bounding_rect": {},
                    }
                ]
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert results == []
