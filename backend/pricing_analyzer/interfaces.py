"""
pricing_analyzer/interfaces.py — Payload types for the Pricing Analyzer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PricingPayload:
    """Typed input for the pricing analyzer."""
    url: str
    body_text: str
