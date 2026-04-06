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

# Size ratio thresholds
_SEMANTIC_RATIO_THRESHOLD = 3.0   # opposing-choice pairs (accept vs decline)
_GENERIC_RATIO_THRESHOLD = 8.0    # unrelated pairs (needs much larger disparity)


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
        """Flag nearby button pairs where one is much larger than the other.

        Three key improvements over the naive approach:
        1. Proximity: only compare buttons within _PROXIMITY_PX vertical distance
        2. Semantic: opposing-choice pairs (accept/decline) use a lower threshold
        3. Dedup:  each smaller element is flagged at most once (worst ratio wins)
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
                area_b = self._get_area(btn_b)
                y_b = self._get_y(btn_b)

                # ── Proximity gate ──
                if abs(y_a - y_b) > _PROXIMITY_PX:
                    continue

                ratio = max(area_a, area_b) / min(area_a, area_b)

                # ── Threshold selection ──
                is_semantic = self._is_semantic_pair(btn_a, btn_b)
                threshold = _SEMANTIC_RATIO_THRESHOLD if is_semantic else _GENERIC_RATIO_THRESHOLD

                if ratio < threshold:
                    continue

                smaller = btn_a if area_a < area_b else btn_b
                larger = btn_a if area_a >= area_b else btn_b

                # Confidence: semantic pairs get a boost
                if is_semantic:
                    confidence = min(0.7 + (ratio - 3) * 0.05, 0.95)
                else:
                    confidence = min(0.5 + (ratio - 8) * 0.05, 0.85)

                explanation_detail = ""
                if is_semantic:
                    explanation_detail = (
                        f" The '{larger.text_content.strip()[:30]}' button is "
                        f"visually dominant over '{smaller.text_content.strip()[:30]}', "
                        f"steering users toward one choice."
                    )

                det = Detection(
                    category="visual_interference",
                    element_selector=smaller.selector,
                    confidence=confidence,
                    explanation=(
                        f"This button is {ratio:.1f}× smaller than a "
                        f"nearby button, making it easy to overlook."
                        f"{explanation_detail}"
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
