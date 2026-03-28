"""Tests for the DOM Analyzer."""

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
    from dom_analyzer.service import DomAnalyzerService
    return DomAnalyzerService()


def _run(coro: object) -> list[Detection]:
    return asyncio.run(coro)  # type: ignore[arg-type]


class TestDomAnalyzer:
    """Unit tests for DomAnalyzerService."""

    def test_analyzer_name_property(self, service: object) -> None:
        assert service.name == "dom"  # type: ignore[attr-defined]

    def test_required_payload_keys(self, service: object) -> None:
        assert service.required_payload_keys == ["dom_metadata"]  # type: ignore[attr-defined]

    def test_detects_prechecked_inputs(self, service: object) -> None:
        payload = {
            "dom_metadata": {
                "hidden_elements": [],
                "interactive_elements": [],
                "prechecked_inputs": [
                    {
                        "selector": "#newsletter-optin",
                        "tag_name": "input",
                        "text_content": "",
                        "attributes": {"type": "checkbox", "checked": ""},
                        "bounding_rect": {"x": 0, "y": 0, "width": 20, "height": 20},
                        "computed_styles": {
                            "color": "black",
                            "background_color": "white",
                            "font_size": "14px",
                            "opacity": "1",
                            "display": "inline",
                            "visibility": "visible",
                        },
                    }
                ],
                "url": "https://example.com",
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert len(results) >= 1
        assert results[0].category == "preselection"
        assert results[0].analyzer_name == "dom"
        assert results[0].platform_context == "general"
        assert "FTC-S5" in results[0].regulation_refs

    def test_returns_empty_on_clean_page(self, service: object) -> None:
        payload = {
            "dom_metadata": {
                "hidden_elements": [],
                "interactive_elements": [],
                "prechecked_inputs": [],
                "url": "https://example.com",
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert results == []

    def test_confidence_scores_are_bounded(self, service: object) -> None:
        payload = {
            "dom_metadata": {
                "hidden_elements": [],
                "interactive_elements": [],
                "prechecked_inputs": [
                    {
                        "selector": "#opt",
                        "tag_name": "input",
                        "text_content": "",
                        "attributes": {"type": "checkbox"},
                        "bounding_rect": {"x": 0, "y": 0, "width": 20, "height": 20},
                        "computed_styles": {
                            "color": "black",
                            "background_color": "white",
                            "font_size": "14px",
                            "opacity": "1",
                            "display": "inline",
                            "visibility": "visible",
                        },
                    }
                ],
                "url": "https://example.com",
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        for det in results:
            assert 0.0 <= det.confidence <= 1.0

    def test_detects_button_size_disparity(self, service: object) -> None:
        payload = {
            "dom_metadata": {
                "hidden_elements": [],
                "interactive_elements": [
                    {
                        "selector": "#accept",
                        "tag_name": "button",
                        "text_content": "Accept All",
                        "attributes": {},
                        "bounding_rect": {"x": 0, "y": 0, "width": 300, "height": 60},
                        "computed_styles": {
                            "color": "white",
                            "background_color": "blue",
                            "font_size": "18px",
                            "opacity": "1",
                            "display": "block",
                            "visibility": "visible",
                        },
                    },
                    {
                        "selector": "#decline",
                        "tag_name": "button",
                        "text_content": "Decline",
                        "attributes": {},
                        "bounding_rect": {"x": 0, "y": 0, "width": 80, "height": 14},
                        "computed_styles": {
                            "color": "gray",
                            "background_color": "white",
                            "font_size": "10px",
                            "opacity": "1",
                            "display": "inline",
                            "visibility": "visible",
                        },
                    },
                ],
                "prechecked_inputs": [],
                "url": "https://example.com",
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        vi_detections = [d for d in results if d.category == "visual_interference"]
        assert len(vi_detections) >= 1
        assert vi_detections[0].analyzer_name == "dom"
        assert "DSA-Art25" in vi_detections[0].regulation_refs
