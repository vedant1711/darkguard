"""
visual_analyzer/service.py — Visual Analyzer Service.

Converts DOM metadata into an ElementMap, then sends it to an LLM for
reasoning about visual dark patterns (layout anomalies, visual interference,
misdirection through design).

Standalone module — imports only from ``core.*`` and own ``interfaces.py``.
Uses ``core.llm_client`` for model-agnostic LLM calls.
Uses ``core.sanitizer`` for pre-LLM PII sanitization (Layer 3).
"""

from __future__ import annotations

import json
import logging

from core.interfaces import BaseAnalyzer
from core.llm_client import LLMError, get_llm_client
from core.models import Detection
from core.sanitizer import sanitize_text
from visual_analyzer.element_map_builder import build_element_map, element_map_to_prompt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a dark-pattern detection expert. Analyze the following structured
page layout (ElementMap) and identify visual dark patterns.

Look for:
1. Visual Interference: buttons with drastically different sizes, low-contrast text/buttons,
   elements with very low opacity that are hard to see
2. Misdirection: prominent "accept" buttons with tiny/hidden "decline" buttons,
   visual hierarchy that steers users toward a specific action

For each issue found, respond with a JSON array of objects:
[
  {
    "selector": "CSS selector of the element",
    "category": "visual_interference" or "misdirection",
    "confidence": 0.0-1.0,
    "explanation": "brief explanation",
    "severity": "low" or "medium" or "high"
  }
]

If no issues are found, respond with an empty array: []
Respond ONLY with the JSON array, no other text."""


class VisualAnalyzerService(BaseAnalyzer):
    """Analyzes page layout via ElementMap → LLM reasoning."""

    @property
    def name(self) -> str:
        return "visual"

    @property
    def required_payload_keys(self) -> list[str]:
        return ["dom_metadata"]

    async def analyze(self, payload: dict[str, object]) -> list[Detection]:
        detections: list[Detection] = []

        dom_metadata = payload.get("dom_metadata")
        if not isinstance(dom_metadata, dict):
            return detections

        # Build the ElementMap from DOM metadata
        element_map = build_element_map(dom_metadata)

        if not element_map.elements:
            return detections

        # Convert to prompt text
        prompt = element_map_to_prompt(element_map)

        # Try LLM analysis via model-agnostic client
        try:
            llm = get_llm_client(purpose="visual_analysis")

            # Layer 3: sanitize prompt before sending to LLM
            sanitized_prompt = sanitize_text(prompt)

            response_text = await llm.generate(
                prompt=sanitized_prompt,
                system=SYSTEM_PROMPT,
            )

            detections = self._parse_llm_response(response_text)

        except LLMError:
            logger.exception(
                "Visual analyzer LLM call failed, falling back to heuristics"
            )
            return self._heuristic_analysis(element_map)

        return detections

    def _parse_llm_response(self, response_text: str) -> list[Detection]:
        """Parse the LLM JSON response into Detection objects."""
        detections: list[Detection] = []

        if not response_text:
            return detections

        # Strip markdown fences if present
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        try:
            raw_detections = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Visual analyzer: could not parse LLM response as JSON")
            return detections

        if isinstance(raw_detections, list):
            for item in raw_detections:
                if isinstance(item, dict):
                    detections.append(
                        Detection(
                            category=str(item.get("category", "visual_interference")),
                            element_selector=str(item.get("selector", "")),
                            confidence=float(item.get("confidence", 0.5)),
                            explanation=str(item.get("explanation", "")),
                            severity=str(item.get("severity", "medium")),  # type: ignore[arg-type]
                            analyzer_name=self.name,
                            platform_context="general",
                            regulation_refs=["DSA-Art25"],
                        )
                    )

        return detections

    def _heuristic_analysis(self, element_map: object) -> list[Detection]:
        """Fallback heuristic analysis when LLM is unavailable."""
        # ElementMap heuristics are handled by the DOM analyzer already;
        # this is a stub for when the visual analyzer has no LLM access.
        _ = element_map
        return []
