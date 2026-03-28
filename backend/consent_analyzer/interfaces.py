"""
consent_analyzer/interfaces.py — Payload types for the Consent Analyzer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConsentButton:
    """A button related to cookie/tracking consent."""
    selector: str
    text: str
    is_primary: bool  # derived from styling/classes
    area: float
    opacity: float


@dataclass
class ConsentCheckbox:
    """A checkbox related to data sharing/tracking."""
    selector: str
    is_checked: bool
    label_text: str


@dataclass
class ConsentPayload:
    """Typed input for the consent analyzer."""
    buttons: list[ConsentButton]
    checkboxes: list[ConsentCheckbox]
    has_consent_banner: bool
    banner_selector: str
