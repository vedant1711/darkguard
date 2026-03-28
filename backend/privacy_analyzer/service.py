"""
privacy_analyzer/service.py — Privacy Analyzer Service.

Rules engine for detecting:
- Privacy Zuckering
- Default data sharing
- Contact spam permissions
"""

from __future__ import annotations

from core.interfaces import BaseAnalyzer
from core.models import Detection
from privacy_analyzer.interfaces import PrivacyInput, PrivacyPayload


class PrivacyAnalyzerService(BaseAnalyzer):
    """Analyzes forms and settings for deceptive privacy defaults."""

    @property
    def name(self) -> str:
        return "privacy"

    @property
    def required_payload_keys(self) -> list[str]:
        return ["dom_metadata"]

    async def analyze(self, payload: dict[str, object]) -> list[Detection]:
        detections: list[Detection] = []
        
        val = self._parse_payload(payload)
        if not val:
            return detections

        detections.extend(self._check_zuckering(val.settings_inputs))

        return detections

    def _parse_payload(self, payload: dict[str, object]) -> PrivacyPayload | None:
        """Extract privacy-related inputs from the DOM metadata."""
        dom_metadata = payload.get("dom_metadata")
        if not isinstance(dom_metadata, dict):
            return None

        # Look for checkboxes and radios in prechecked_inputs and interactive_elements
        inputs: list[PrivacyInput] = []
        
        prechecked = dom_metadata.get("prechecked_inputs", [])
        if isinstance(prechecked, list):
            for el in prechecked:
                if not isinstance(el, dict):
                    continue
                tag = str(el.get("tag_name", "")).lower()
                if tag == "input":
                    inputs.append(
                        PrivacyInput(
                            selector=str(el.get("selector", "")),
                            is_checked=True,
                            label_text=str(el.get("text_content", "")),
                        )
                    )

        # We also might check interactive_elements if we needed to see unchecked defaults,
        # but for Privacy Zuckering, the dark pattern is when it is PRE-CHECKED to share.

        return PrivacyPayload(
            url=str(dom_metadata.get("url", "")),
            settings_inputs=inputs,
        )

    def _check_zuckering(self, inputs: list[PrivacyInput]) -> list[Detection]:
        """Flag pre-checked settings that compromise privacy."""
        detections: list[Detection] = []
        
        zuckering_keywords = [
            "public", "share", "third party", "partners", "contacts", 
            "address book", "discoverable", "search engine"
        ]

        for inp in inputs:
            if not inp.is_checked:
                continue
                
            txt = inp.label_text.lower()
            
            # If it's a pre-ticked box about making data public or sharing it
            if any(k in txt for k in zuckering_keywords):
                # Ensure it's not a negate clause like "do not share"
                if "do not" not in txt and "don't" not in txt and "never" not in txt:
                    detections.append(
                        Detection(
                            category="privacy_zuckering",
                            element_selector=inp.selector,
                            confidence=0.9,
                            explanation=(
                                "A setting to share data or make info public is "
                                "pre-selected by default. Privacy-invasive options "
                                "should require explicit opt-in."
                            ),
                            severity="high",
                            analyzer_name=self.name,
                            platform_context="social_media", # Commonly found here
                            regulation_refs=["GDPR-Art25", "CCPA"],
                        )
                    )
        return detections
