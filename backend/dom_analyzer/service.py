"""
dom_analyzer/service.py — DOM Analyzer Service.

Rules engine that detects dark patterns from DOM metadata:
- Visual interference (contrast ratios, size disparity between competing choices)
- Pre-selected checkboxes
- Hidden elements that may be deceptive

Standalone module — imports only from ``core.*``.
"""

from __future__ import annotations

import re

from core.interfaces import BaseAnalyzer
from core.models import Detection
from dom_analyzer.interfaces import DomElementInfo, DomPayload

# ── Semantic button-pair detection ──────────────────────
# These patterns identify button text that suggests opposing choices.
_ACCEPT_RE = re.compile(
    r"(accept|agree|allow|yes|confirm|continue|ok|got it|i understand|subscribe|sign.?up|buy|add.?to.?cart)",
    re.IGNORECASE,
)
_DECLINE_RE = re.compile(
    r"(reject|decline|deny|no|cancel|dismiss|close|skip|not now|maybe later|no thanks|i don.?t want)",
    re.IGNORECASE,
)

# Maximum vertical distance (px) for two buttons to be considered "nearby"
_PROXIMITY_PX = 300

# Size ratio threshold for opposing-choice button pairs
_SEMANTIC_RATIO_THRESHOLD = 3.0   # accept vs decline, agree vs disagree, etc.


class DomAnalyzerService(BaseAnalyzer):
    """Analyzes DOM metadata for dark-pattern signals."""

    @property
    def name(self) -> str:
        return "dom"

    @property
    def required_payload_keys(self) -> list[str]:
        return ["dom_metadata"]

    async def analyze(self, payload: dict[str, object]) -> list[Detection]:
        detections: list[Detection] = []

        # Convert raw dict → typed DomPayload
        dom_payload = self._parse_payload(payload)
        if dom_payload is None:
            return detections

        # Check pre-selected inputs
        for el in dom_payload.prechecked_inputs:
            detections.append(
                Detection(
                    category="preselection",
                    element_selector=el.selector,
                    confidence=0.85,
                    explanation=(
                        "This checkbox/radio is pre-selected, which may "
                        "trick users into opting in unintentionally."
                    ),
                    severity="medium",
                    analyzer_name=self.name,
                    platform_context="general",
                    regulation_refs=["FTC-S5", "DSA-Art25"],
                )
            )

        # Check interactive element size disparity (proximity + semantic aware)
        detections.extend(self._check_size_disparity(dom_payload.interactive_elements))
        detections.extend(self._check_low_contrast(dom_payload.interactive_elements))
        detections.extend(self._check_hidden_deception(dom_payload.hidden_elements))
        detections.extend(self._check_disguised_ads(dom_payload.interactive_elements))
        detections.extend(self._check_comparison_prevention(dom_payload.interactive_elements))

        return detections

    def _parse_payload(self, payload: dict[str, object]) -> DomPayload | None:
        """Convert raw payload dict → typed DomPayload."""
        dom_metadata = payload.get("dom_metadata", {})
        if not isinstance(dom_metadata, dict):
            return None

        def _parse_elements(key: str) -> list[DomElementInfo]:
            raw = dom_metadata.get(key, [])
            if not isinstance(raw, list):
                return []
            elements: list[DomElementInfo] = []
            for el in raw:
                if isinstance(el, dict):
                    elements.append(
                        DomElementInfo(
                            selector=str(el.get("selector", "")),
                            tag_name=str(el.get("tag_name", "")),
                            text_content=str(el.get("text_content", "")),
                            attributes=el.get("attributes", {}),  # type: ignore[arg-type]
                            bounding_rect=el.get("bounding_rect", {}),  # type: ignore[arg-type]
                            computed_styles=el.get("computed_styles", {}),  # type: ignore[arg-type]
                        )
                    )
            return elements

        return DomPayload(
            hidden_elements=_parse_elements("hidden_elements"),
            interactive_elements=_parse_elements("interactive_elements"),
            prechecked_inputs=_parse_elements("prechecked_inputs"),
            url=str(dom_metadata.get("url", "")),
        )

    # ── Helpers ──────────────────────────────────────────

    @staticmethod
    def _get_area(el: DomElementInfo) -> float:
        return float(el.bounding_rect.get("width", 0)) * float(
            el.bounding_rect.get("height", 0)
        )

    @staticmethod
    def _get_y(el: DomElementInfo) -> float:
        return float(el.bounding_rect.get("y", 0))

    @staticmethod
    def _is_semantic_pair(a: DomElementInfo, b: DomElementInfo) -> bool:
        """Check if two buttons represent an opposing-choice pair."""
        text_a = a.text_content.strip().lower()
        text_b = b.text_content.strip().lower()

        a_is_accept = bool(_ACCEPT_RE.search(text_a))
        a_is_decline = bool(_DECLINE_RE.search(text_a))
        b_is_accept = bool(_ACCEPT_RE.search(text_b))
        b_is_decline = bool(_DECLINE_RE.search(text_b))

        # One must be accept-like and the other decline-like
        return (a_is_accept and b_is_decline) or (a_is_decline and b_is_accept)

    # ── Size disparity check ─────────────────────────────

    def _check_size_disparity(
        self, elements: list[DomElementInfo]
    ) -> list[Detection]:
        """Flag opposing-choice button pairs where one is much larger.

        ONLY compares buttons that represent competing choices:
        accept/decline, agree/disagree, subscribe/cancel, etc.
        Random unrelated buttons are never compared.
        """
        buttons = [
            e for e in elements
            if e.tag_name in ("button", "a") and self._get_area(e) > 0
        ]

        # best_detection_per_small_selector: selector → (ratio, Detection)
        best: dict[str, tuple[float, Detection]] = {}

        for i, btn_a in enumerate(buttons):
            area_a = self._get_area(btn_a)
            y_a = self._get_y(btn_a)

            for btn_b in buttons[i + 1:]:
                # ── Must be an opposing-choice pair ──
                if not self._is_semantic_pair(btn_a, btn_b):
                    continue

                area_b = self._get_area(btn_b)
                y_b = self._get_y(btn_b)

                # ── Proximity gate ──
                if abs(y_a - y_b) > _PROXIMITY_PX:
                    continue

                ratio = max(area_a, area_b) / min(area_a, area_b)

                if ratio < _SEMANTIC_RATIO_THRESHOLD:
                    continue

                smaller = btn_a if area_a < area_b else btn_b
                larger = btn_a if area_a >= area_b else btn_b

                confidence = min(0.7 + (ratio - 3) * 0.05, 0.95)

                det = Detection(
                    category="visual_interference",
                    element_selector=smaller.selector,
                    confidence=confidence,
                    explanation=(
                        f"The '{larger.text_content.strip()[:40]}' button is "
                        f"{ratio:.1f}× larger than '{smaller.text_content.strip()[:40]}', "
                        f"steering users toward one choice."
                    ),
                    severity="medium" if ratio < 5 else "high",
                    analyzer_name=self.name,
                    platform_context="general",
                    regulation_refs=["DSA-Art25", "UCPD"],
                )

                # Dedup: keep only the worst ratio per smaller element
                sel = smaller.selector
                if sel not in best or ratio > best[sel][0]:
                    best[sel] = (ratio, det)

        return [det for _, det in best.values()]

    # ── Low contrast / opacity check ─────────────────────

    def _check_low_contrast(
        self, elements: list[DomElementInfo]
    ) -> list[Detection]:
        """Flag elements with very low text contrast (grey-on-grey)."""
        detections: list[Detection] = []

        for el in elements:
            opacity = el.computed_styles.get("opacity", "1")
            try:
                opacity_val = float(opacity)
            except (ValueError, TypeError):
                opacity_val = 1.0

            if opacity_val < 0.4:
                detections.append(
                    Detection(
                        category="visual_interference",
                        element_selector=el.selector,
                        confidence=0.8,
                        explanation=(
                            f"This element has very low opacity ({opacity_val:.2f}), "
                            f"making it hard to see or read."
                        ),
                        severity="medium",
                        analyzer_name=self.name,
                        platform_context="general",
                        regulation_refs=["DSA-Art25"],
                    )
                )

        return detections

    # ── Hidden element deception check ───────────────────

    _DECEPTIVE_HIDDEN_RE = re.compile(
        r"(subscribe|newsletter|opt.?in|sign.?up|marketing|promotional|notification)",
        re.IGNORECASE,
    )

    def _check_hidden_deception(
        self, hidden_elements: list[DomElementInfo]
    ) -> list[Detection]:
        """Flag hidden elements whose text suggests deceptive opt-ins."""
        detections: list[Detection] = []

        for el in hidden_elements:
            text = el.text_content.strip()
            if not text or len(text) < 5:
                continue

            if self._DECEPTIVE_HIDDEN_RE.search(text):
                detections.append(
                    Detection(
                        category="hidden_costs",
                        element_selector=el.selector,
                        confidence=0.75,
                        explanation=(
                            f"A hidden element contains opt-in language: "
                            f"\"{text[:80]}\". This may trick users into "
                            f"subscribing without their knowledge."
                        ),
                        severity="high",
                        analyzer_name=self.name,
                        platform_context="general",
                        regulation_refs=["FTC-S5", "DSA-Art25"],
                    )
                )

        return detections

    # ── Disguised ads detection ───────────────────────────

    _AD_CLASS_RE = re.compile(
        r"(^|[_-])(ad|ads|advert|sponsored|promotion|promo|partner|paid)([_-]|$)",
        re.IGNORECASE,
    )
    _AD_ATTR_RE = re.compile(
        r"(sponsored|advertisement|promoted|paid.?content|partner.?content)",
        re.IGNORECASE,
    )

    def _check_disguised_ads(
        self, elements: list[DomElementInfo]
    ) -> list[Detection]:
        """Flag elements that appear to be ads disguised as regular content."""
        detections: list[Detection] = []

        for el in elements:
            attrs = el.attributes
            class_str = attrs.get("class", "")
            id_str = attrs.get("id", "")
            text = el.text_content.strip().lower()

            # Check classes and IDs for ad indicators
            has_ad_class = bool(self._AD_CLASS_RE.search(class_str) or self._AD_CLASS_RE.search(id_str))

            # Check attributes for ad indicators
            has_ad_attr = any(
                self._AD_ATTR_RE.search(str(v))
                for v in attrs.values()
            )

            # Check text for small "sponsored" / "ad" labels
            has_ad_text = text in ("ad", "ads", "sponsored", "promoted", "advertisement")

            if has_ad_class or has_ad_attr or has_ad_text:
                detections.append(
                    Detection(
                        category="disguised_ads",
                        element_selector=el.selector,
                        confidence=0.7,
                        explanation=(
                            f"This element appears to be a sponsored/advertising element "
                            f"styled to blend in with regular content. Disguised ads "
                            f"can mislead users into clicking on paid content."
                        ),
                        severity="medium",
                        analyzer_name=self.name,
                        platform_context="general",
                        regulation_refs=["FTC-S5", "DSA-Art25"],
                    )
                )

        return detections

    # ── Comparison prevention detection ──────────────────

    def _check_comparison_prevention(
        self, elements: list[DomElementInfo]
    ) -> list[Detection]:
        """Flag disabled or hidden comparison features."""
        detections: list[Detection] = []

        for el in elements:
            attrs = el.attributes
            text = el.text_content.strip().lower()

            # Check for disabled comparison elements
            is_compare_related = any(
                kw in text for kw in ("compare", "comparison", "side by side", "vs")
            )
            is_disabled = (
                "disabled" in attrs
                or attrs.get("aria-disabled") == "true"
                or el.computed_styles.get("pointer-events") == "none"
            )

            if is_compare_related and is_disabled:
                detections.append(
                    Detection(
                        category="comparison_prevention",
                        element_selector=el.selector,
                        confidence=0.7,
                        explanation=(
                            f"A comparison feature appears to be disabled or blocked. "
                            f"This may prevent users from making informed decisions "
                            f"by comparing options side by side."
                        ),
                        severity="medium",
                        analyzer_name=self.name,
                        platform_context="ecommerce",
                        regulation_refs=["UCPD", "CRD-Art6"],
                    )
                )

        return detections
