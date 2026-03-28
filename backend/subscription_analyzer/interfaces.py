"""
subscription_analyzer/interfaces.py — Payload types for Subscription Analyzer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SubscriptionPayload:
    """Typed input for the subscription analyzer."""
    url: str
    body_text: str
    headings: list[str] = field(default_factory=list)
    buttons: list[str] = field(default_factory=list)
