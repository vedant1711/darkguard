"""
privacy_analyzer/interfaces.py — Payload types for the Privacy Analyzer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PrivacyInput:
    """A checkbox or toggle related to privacy settings."""
    selector: str
    is_checked: bool
    label_text: str


@dataclass
class PrivacyPayload:
    """Typed input for the privacy analyzer."""
    url: str
    settings_inputs: list[PrivacyInput] = field(default_factory=list)
