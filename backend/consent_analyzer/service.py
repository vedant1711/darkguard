"""
consent_analyzer/service.py — Consent Analyzer Service.

Rules engine specifically tuned for EU/GDPR consent dark patterns:
- Asymmetric choices (Accept All vs. Manage Settings)
- Pre-checked tracking boxes
- Hidden/buried decline options

Standalone module — imports only from ``core.*`` and own ``interfaces.py``.
"""

from __future__ import annotations

import re

from consent_analyzer.interfaces import ConsentButton, ConsentCheckbox, ConsentPayload
from core.interfaces import BaseAnalyzer
from core.models import Detection

# Heuristics for consent classification
ACCEPT_RE = re.compile(r"^(accept|agree|allow)(\s+all)?(\s+cookies?)?$", re.IGNORECASE)
DECLINE_RE = re.compile(r"^(reject|decline|deny)(\s+all)?(\s+cookies?)?$", re.IGNORECASE)
MANAGE_RE = re.compile(r"^(manage|settings|preferences|customize|options)(\s+(settings|cookies?|preferences|choices))?$", re.IGNORECASE)


class ConsentAnalyzerService(BaseAnalyzer):
    """Analyzes cookie/consent banners for deceptive design."""

    @property
    def name(self) -> str:
        return "consent"

    @property
    def required_payload_keys(self) -> list[str]:
        # We need DOM structure to find the banners/checkboxes
        return ["dom_metadata"]

    async def analyze(self, payload: dict[str, object]) -> list[Detection]:
        detections: list[Detection] = []

        val = self._parse_payload(payload)
        if not val or not val.has_consent_banner:
            return detections

        # 1. Check for asymmetric accept/reject choices
        detections.extend(self._check_asymmetry(val.buttons))

        # 2. Check for pre-ticked tracking checkboxes
        detections.extend(self._check_preticked(val.checkboxes))

        return detections

    def _parse_payload(self, payload: dict[str, object]) -> ConsentPayload | None:
        """Extract consent-specific elements from the raw dom_metadata."""
        dom_metadata = payload.get("dom_metadata")
        if not isinstance(dom_metadata, dict):
            return None

        interactive = dom_metadata.get("interactive_elements", [])
        if not isinstance(interactive, list):
            return None

        # Look for a likely consent banner
        has_banner = False
        banner_selector = ""
        buttons: list[ConsentButton] = []
        checkboxes: list[ConsentCheckbox] = []

        # Very basic heuristic scanning the raw DOM data
        for el in interactive:
            if not isinstance(el, dict):
                continue

            tag = str(el.get("tag_name", "")).lower()
            text = str(el.get("text_content", "")).strip()
            attrs = el.get("attributes", {})
            styles = el.get("computed_styles", {})
            rect = el.get("bounding_rect", {})

            if not isinstance(attrs, dict) or not isinstance(styles, dict) or not isinstance(rect, dict):
                continue

            # Identify banner strings
            if "cookie" in text.lower() or "consent" in text.lower():
                has_banner = True

            if tag in ("button", "a") and len(text) < 30:
                area = float(rect.get("width", 0)) * float(rect.get("height", 0))
                # Heuristic for primary button: has a distinct background color vs the page, or styled bolder
                bg_color = str(styles.get("background_color", ""))
                is_primary = bg_color not in ("", "transparent", "white", "#ffffff", "none", "rgba(0, 0, 0, 0)")

                opacity_str = styles.get("opacity", "1")
                try:
                    opacity = float(opacity_str)
                except ValueError:
                    opacity = 1.0

                buttons.append(
                    ConsentButton(
                        selector=str(el.get("selector", "")),
                        text=text,
                        is_primary=is_primary,
                        area=area,
                        opacity=opacity,
                    )
                )

        # Checkboxes are usually in 'prechecked_inputs' or normal inputs
        prechecked = dom_metadata.get("prechecked_inputs", [])
        if isinstance(prechecked, list):
            for el in prechecked:
                if isinstance(el, dict) and str(el.get("attributes", {}).get("type", "")) == "checkbox":
                    checkboxes.append(
                        ConsentCheckbox(
                            selector=str(el.get("selector", "")),
                            is_checked=True,
                            label_text=str(el.get("text_content", "")),
                        )
                    )

        # Only process if we found evidence of a consent interaction
        has_consent_terms = any(b.text for b in buttons if ACCEPT_RE.search(b.text) or MANAGE_RE.search(b.text))
        
        if not has_banner and not has_consent_terms:
            return None

        return ConsentPayload(
            buttons=buttons,
            checkboxes=checkboxes,
            has_consent_banner=True,
            banner_selector=banner_selector,
        )

    def _check_asymmetry(self, buttons: list[ConsentButton]) -> list[Detection]:
        """Flag instances where 'Accept' is prominent but 'Reject' is hidden/missing."""
        detections: list[Detection] = []

        accept_btns = [b for b in buttons if ACCEPT_RE.search(b.text)]
        reject_btns = [b for b in buttons if DECLINE_RE.search(b.text)]
        manage_btns = [b for b in buttons if MANAGE_RE.search(b.text)]

        if not accept_btns:
            return detections

        best_accept = sorted(accept_btns, key=lambda b: b.area, reverse=True)[0]

        # Scenario 1: No reject button at all (only accept or manage)
        if not reject_btns and manage_btns:
            best_manage = sorted(manage_btns, key=lambda b: b.area, reverse=True)[0]
            detections.append(
                Detection(
                    category="asymmetric_choice",
                    element_selector=best_accept.selector,
                    confidence=0.9,
                    explanation=(
                        "Consent banner offers a 1-click 'Accept' but requires "
                        "navigating through settings to reject (no 1-click 'Reject')."
                    ),
                    severity="high",
                    analyzer_name=self.name,
                    platform_context="consent",
                    regulation_refs=["GDPR-Art7", "ePrivacy"],
                )
            )
            return detections

        # Scenario 2: Reject button exists but is visually de-emphasized
        if reject_btns:
            best_reject = sorted(reject_btns, key=lambda b: b.area, reverse=True)[0]
            
            # Massive size difference
            if best_accept.area > 0 and best_reject.area > 0:
                if best_accept.area / best_reject.area >= 2.0:
                    detections.append(
                        Detection(
                            category="visual_interference",
                            element_selector=best_reject.selector,
                            confidence=0.85,
                            explanation=(
                                f"'Accept' button is {best_accept.area/best_reject.area:.1f}x "
                                f"larger than the 'Reject' button."
                            ),
                            severity="medium",
                            analyzer_name=self.name,
                            platform_context="consent",
                            regulation_refs=["GDPR-Art7", "DSA-Art25"],
                        )
                    )
            
            # Primary vs secondary styling
            if best_accept.is_primary and not best_reject.is_primary:
                detections.append(
                    Detection(
                        category="visual_interference",
                        element_selector=best_accept.selector,
                        confidence=0.75,
                        explanation=(
                            "'Accept' uses prominent primary styling while "
                            "'Reject' is styled as a less visible secondary link."
                        ),
                        severity="medium",
                        analyzer_name=self.name,
                        platform_context="consent",
                        regulation_refs=["GDPR-Art7", "DSA-Art25"],
                    )
                )

        return detections

    def _check_preticked(self, checkboxes: list[ConsentCheckbox]) -> list[Detection]:
        """Flag pre-ticked checkboxes in a consent context."""
        detections: list[Detection] = []
        for cb in checkboxes:
            # If it's pre-checked and we are in a consent banner
            if cb.is_checked:
                txt = cb.label_text.lower()
                # If it's evidently a tracking/marketing cookie
                if "marketing" in txt or "analytics" in txt or "tracking" in txt or "personal" in txt:
                    detections.append(
                        Detection(
                            category="prechecked_consent",
                            element_selector=cb.selector,
                            confidence=0.95,
                            explanation=(
                                "Non-essential cookies (marketing/analytics) are pre-selected "
                                "by default on the consent form."
                            ),
                            severity="high",
                            analyzer_name=self.name,
                            platform_context="consent",
                            regulation_refs=["GDPR-Art7", "ePrivacy"],
                        )
                    )
        return detections
