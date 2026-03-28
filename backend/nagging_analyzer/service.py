"""
nagging_analyzer/service.py — Nagging Analyzer Service.

Rules engine for detecting:
- Persistent popups
- Notification inflation
- Un-dismissible overlays
"""

from __future__ import annotations

from core.interfaces import BaseAnalyzer
from core.models import Detection
from nagging_analyzer.interfaces import NaggingEvent, NaggingPayload


class NaggingAnalyzerService(BaseAnalyzer):
    """Analyzes interruptive events for nagging behavior."""

    @property
    def name(self) -> str:
        return "nagging"

    @property
    def required_payload_keys(self) -> list[str]:
        return ["nagging_events"]

    async def analyze(self, payload: dict[str, object]) -> list[Detection]:
        detections: list[Detection] = []
        
        val = self._parse_payload(payload)
        if not val:
            return detections

        detections.extend(self._check_nagging_frequency(val.events))
        detections.extend(self._check_persistent_overlay(val.has_persistent_overlay))

        return detections

    def _parse_payload(self, payload: dict[str, object]) -> NaggingPayload | None:
        """Extract nagging event data from the payload."""
        nag_data = payload.get("nagging_events")
        if not isinstance(nag_data, dict):
            return None

        has_overlay = bool(nag_data.get("has_persistent_overlay", False))
        
        raw_events = nag_data.get("events", [])
        parsed_events: list[NaggingEvent] = []
        
        if isinstance(raw_events, list):
            for e in raw_events:
                if not isinstance(e, dict):
                    continue
                try:
                    ts = float(e.get("timestamp", 0.0))
                except (ValueError, TypeError):
                    ts = 0.0
                    
                parsed_events.append(
                    NaggingEvent(
                        event_type=str(e.get("type", "unknown")).lower(),
                        text=str(e.get("text", "")),
                        timestamp=ts,
                    )
                )

        return NaggingPayload(
            url=str(payload.get("url", "")),
            has_persistent_overlay=has_overlay,
            events=parsed_events,
        )

    def _check_nagging_frequency(self, events: list[NaggingEvent]) -> list[Detection]:
        """Flag instances where users are repeatedly interrupted."""
        detections: list[Detection] = []
        
        # Look for repeated identical requests or simply high volume of interrupts
        notification_prompts = [e for e in events if e.event_type == "notification_prompt"]
        modals = [e for e in events if e.event_type in ("modal", "app_install_prompt")]

        # Pattern: Repeated requests for notifications after dismissal
        if len(notification_prompts) >= 2:
            detections.append(
                Detection(
                    category="notification_inflation",
                    element_selector="window",
                    confidence=0.9,
                    explanation=(
                        f"Site triggered {len(notification_prompts)} separate "
                        f"notification permission requests, aggressively nagging "
                        f"the user."
                    ),
                    severity="high",
                    analyzer_name=self.name,
                    platform_context="social_media", # Or general
                    regulation_refs=["GDPR-Art7", "ePrivacy"],
                )
            )

        # Pattern: Excessive popups
        if len(modals) >= 3:
            detections.append(
                Detection(
                    category="persistent_nagging",
                    element_selector="document",
                    confidence=0.85,
                    explanation=(
                        f"Site triggered {len(modals)} interruptive popups "
                        f"or modals within the analyzed session."
                    ),
                    severity="medium",
                    analyzer_name=self.name,
                    platform_context="general",
                    regulation_refs=["FTC-S5"],
                )
            )

        return detections

    def _check_persistent_overlay(self, has_overlay: bool) -> list[Detection]:
        """Flag overlays that block content and lack a dismiss button."""
        detections: list[Detection] = []
        if has_overlay:
            detections.append(
                Detection(
                    category="persistent_nagging",
                    element_selector="overlay",
                    confidence=0.9,
                    explanation=(
                        "Detected a persistent overlay or modal blocking content "
                        "that appears intentionally difficult to dismiss."
                    ),
                    severity="high",
                    analyzer_name=self.name,
                    platform_context="general",
                    regulation_refs=["FTC-S5", "DSA-Art25"],
                )
            )
        return detections
