"""
checkout_flow_analyzer/interfaces.py — Payload types for Checkout Flow Analyzer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CheckoutItem:
    """An individual line item in the shopping cart/checkout."""
    name: str
    price: float
    is_user_added: bool
    item_type: str  # e.g., "product", "addon", "fee", "tax", "shipping"


@dataclass
class CheckoutPayload:
    """Typed input for the checkout flow analyzer."""
    advertised_price: float | None
    final_price: float
    items: list[CheckoutItem] = field(default_factory=list)
