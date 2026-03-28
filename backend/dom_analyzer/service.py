"""
dom_analyzer/service.py — DOM Analyzer Service.

Rules engine that detects dark patterns from DOM metadata:
- Visual interference (contrast ratios, size disparity)
- Pre-selected checkboxes
- Hidden elements that may be deceptive

Standalone module — imports only from ``core.*``.
"""

from __future__ import annotations

from core.interfaces import BaseAnalyzer
from core.models import Detection
from dom_analyzer.interfaces import DomElementInfo, DomPayload


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

        # Check interactive element size disparity
        detections.extend(self._check_size_disparity(dom_payload.interactive_elements))
        detections.extend(self._check_low_contrast(dom_payload.interactive_elements))

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

    def _check_size_disparity(
        self, elements: list[DomElementInfo]
    ) -> list[Detection]:
        """Flag button pairs where accept is much larger than decline."""
        detections: list[Detection] = []
        buttons = [
            e for e in elements
            if e.tag_name in ("button", "a")
        ]

        for i, btn_a in enumerate(buttons):
            area_a = float(btn_a.bounding_rect.get("width", 0)) * float(
                btn_a.bounding_rect.get("height", 0)
            )

            for btn_b in buttons[i + 1:]:
                area_b = float(btn_b.bounding_rect.get("width", 0)) * float(
                    btn_b.bounding_rect.get("height", 0)
                )

                if area_a == 0 or area_b == 0:
                    continue

                ratio = max(area_a, area_b) / min(area_a, area_b)
                if ratio > 3.0:
                    smaller = btn_a if area_a < area_b else btn_b
                    detections.append(
                        Detection(
                            category="visual_interference",
                            element_selector=smaller.selector,
                            confidence=min(0.5 + (ratio - 3) * 0.1, 0.95),
                            explanation=(
                                f"This button is {ratio:.1f}× smaller than a "
                                f"nearby button, making it easy to overlook."
                            ),
                            severity="medium" if ratio < 5 else "high",
                            analyzer_name=self.name,
                            platform_context="general",
                            regulation_refs=["DSA-Art25"],
                        )
                    )
        return detections

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
