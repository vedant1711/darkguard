"""
nagging_analyzer/interfaces.py — Payload types for the Nagging Analyzer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NaggingEvent:
    """An interruptive event recorded by the frontend."""
    event_type: str  # e.g., "modal", "notification_prompt", "app_install_prompt", "overlay"
    text: str
    timestamp: float


@dataclass
class NaggingPayload:
    """Typed input for the nagging analyzer."""
    url: str
    has_persistent_overlay: bool
    events: list[NaggingEvent] = field(default_factory=list)
