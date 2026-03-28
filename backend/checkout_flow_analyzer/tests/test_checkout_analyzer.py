"""Tests for the Checkout Flow Analyzer."""

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
    from checkout_flow_analyzer.service import CheckoutFlowAnalyzerService
    return CheckoutFlowAnalyzerService()


def _run(coro: object) -> list[Detection]:
    return asyncio.run(coro)  # type: ignore[arg-type]


class TestCheckoutFlowAnalyzer:
    """Unit tests for CheckoutFlowAnalyzerService."""

    def test_analyzer_name_property(self, service: object) -> None:
        assert service.name == "checkout_flow"  # type: ignore[attr-defined]

    def test_required_payload_keys(self, service: object) -> None:
        assert service.required_payload_keys == ["checkout_flow"]  # type: ignore[attr-defined]

    def test_detects_basket_sneaking(self, service: object) -> None:
        payload = {
            "checkout_flow": {
                "advertised_price": 99.0,
                "final_price": 114.0,
                "items": [
                    {"name": "Flight Ticket", "price": 99.0, "is_user_added": True, "item_type": "product"},
                    {"name": "Travel Insurance", "price": 15.0, "is_user_added": False, "item_type": "addon"},
                ]
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        sn_results = [r for r in results if r.category == "basket_sneaking"]
        assert len(sn_results) == 1
        assert "Travel Insurance" in sn_results[0].explanation
        assert "CRD-Art22" in sn_results[0].regulation_refs

    def test_detects_drip_pricing(self, service: object) -> None:
        payload = {
            "checkout_flow": {
                "advertised_price": 40.0,
                "final_price": 55.0,
                "items": [
                    {"name": "Concert Ticket", "price": 40.0, "is_user_added": True, "item_type": "product"},
                    {"name": "Convenience Fee", "price": 15.0, "is_user_added": False, "item_type": "fee"},
                ]
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        dp_results = [r for r in results if r.category == "drip_pricing"]
        assert len(dp_results) == 1
        assert "Convenience Fee" in dp_results[0].explanation
        assert "CRD-Art6" in dp_results[0].regulation_refs

    def test_ignores_clean_checkout(self, service: object) -> None:
        payload = {
            "checkout_flow": {
                "advertised_price": 100.0,
                "final_price": 110.0,
                "items": [
                    {"name": "Shoes", "price": 100.0, "is_user_added": True, "item_type": "product"},
                    {"name": "Shipping", "price": 10.0, "is_user_added": False, "item_type": "shipping"},
                ]
            }
        }
        results = _run(service.analyze(payload))  # type: ignore[attr-defined]
        assert len(results) == 0
