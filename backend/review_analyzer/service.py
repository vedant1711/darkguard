"""
review_analyzer/service.py — Review Analyzer Service.

Detects fake social proof by analyzing review text:
- Burst patterns (many similar reviews in a short span)
- Templated/repetitive praise
- Suspiciously generic language via LLM

Standalone module — imports only from ``core.*`` and own ``interfaces.py``.
Uses ``core.llm_client`` for model-agnostic LLM calls.
Uses ``core.sanitizer`` for pre-LLM PII sanitization (Layer 3).
"""

from __future__ import annotations

import json
import logging
import re

from core.interfaces import BaseAnalyzer
from core.llm_client import LLMError, get_llm_client
from core.models import Detection
from core.sanitizer import sanitize_text
from review_analyzer.interfaces import ReviewPayload

logger = logging.getLogger(__name__)

# Heuristic patterns for fake reviews
GENERIC_PRAISE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(great|amazing|excellent|fantastic|awesome)\s+(product|item|purchase)", re.IGNORECASE),
    re.compile(r"(highly\s+recommend|must\s+buy|best\s+purchase)", re.IGNORECASE),
    re.compile(r"(five\s+stars?|5\s+stars?|⭐{3,})", re.IGNORECASE),
    re.compile(r"(exceeded\s+expectations?|love\s+it|perfect)", re.IGNORECASE),
]

SYSTEM_PROMPT = """You are a fake-review detection expert. Analyze the following review texts
and identify signs of fake social proof or manipulated reviews.

Look for:
1. Templated/repetitive language across reviews
2. Suspiciously generic praise without specific details
3. Burst patterns (many similar-sounding reviews)
4. Overly positive language with no constructive criticism

For each issue found, respond with a JSON array of objects:
[
  {
    "category": "fake_social_proof",
    "confidence": 0.0-1.0,
    "explanation": "brief explanation",
    "severity": "low" or "medium" or "high"
  }
]

If no issues are found, respond with an empty array: []
Respond ONLY with the JSON array, no other text."""


class ReviewAnalyzerService(BaseAnalyzer):
    """Analyzes review text for fake social-proof patterns."""

    @property
    def name(self) -> str:
        return "review"

    @property
    def required_payload_keys(self) -> list[str]:
        return ["review_text"]

    async def analyze(self, payload: dict[str, object]) -> list[Detection]:
        # Convert raw dict → typed ReviewPayload
        review_payload = self._parse_payload(payload)
        if review_payload is None:
            return []

        review_text = review_payload.review_text.strip()
        if len(review_text) < 20:
            return []

        # Split into individual reviews
        reviews = [r.strip() for r in review_text.split("---") if r.strip()]

        # Heuristic analysis first
        detections = self._heuristic_analysis(reviews)

        # LLM analysis if available and enough reviews
        if len(reviews) >= 3:
            llm_detections = await self._llm_analysis(review_text)
            detections.extend(llm_detections)

        return detections

    def _parse_payload(self, payload: dict[str, object]) -> ReviewPayload | None:
        """Convert raw payload dict → typed ReviewPayload."""
        review_text = payload.get("review_text")
        if not review_text or not isinstance(review_text, str):
            return None
        url = str(payload.get("url", ""))
        return ReviewPayload(review_text=review_text, url=url)

    def _heuristic_analysis(self, reviews: list[str]) -> list[Detection]:
        """Rule-based fake review detection."""
        detections: list[Detection] = []

        if len(reviews) < 2:
            return detections

        # Check for generic praise patterns
        generic_count = 0
        for review in reviews:
            for pattern in GENERIC_PRAISE_PATTERNS:
                if pattern.search(review):
                    generic_count += 1
                    break

        if len(reviews) >= 3 and generic_count / len(reviews) > 0.6:
            detections.append(
                Detection(
                    category="fake_social_proof",
                    element_selector="[itemprop='reviewBody']",
                    confidence=0.7,
                    explanation=(
                        f"{generic_count} of {len(reviews)} reviews use generic "
                        f"praise patterns, suggesting templated or fake reviews."
                    ),
                    severity="medium",
                    analyzer_name=self.name,
                    platform_context="ecommerce",
                    regulation_refs=["FTC-S5"],
                )
            )

        # Check for suspiciously similar reviews (burst pattern)
        if len(reviews) >= 5:
            similar_pairs = 0
            total_pairs = 0
            words_per_review = [set(r.lower().split()) for r in reviews]

            for i in range(len(reviews)):
                for j in range(i + 1, len(reviews)):
                    total_pairs += 1
                    overlap = words_per_review[i] & words_per_review[j]
                    if len(overlap) > max(5, min(len(words_per_review[i]), len(words_per_review[j])) * 0.4):
                        similar_pairs += 1

            if total_pairs > 0 and similar_pairs / total_pairs > 0.3:
                detections.append(
                    Detection(
                        category="fake_social_proof",
                        element_selector="[itemprop='reviewBody']",
                        confidence=0.75,
                        explanation=(
                            f"{similar_pairs} review pairs share unusually high "
                            f"word overlap, suggesting burst-generated reviews."
                        ),
                        severity="high",
                        analyzer_name=self.name,
                        platform_context="ecommerce",
                        regulation_refs=["FTC-S5"],
                    )
                )

        return detections

    async def _llm_analysis(self, review_text: str) -> list[Detection]:
        """LLM-based fake review detection via model-agnostic client."""
        detections: list[Detection] = []

        try:
            llm = get_llm_client(purpose="review_analysis")

            # Layer 3: sanitize review text before sending to LLM
            sanitized_text = sanitize_text(review_text[:3000])

            response_text = await llm.generate(
                prompt=sanitized_text,
                system=SYSTEM_PROMPT,
            )

            if not response_text:
                return detections

            # Strip markdown fences if present
            text = response_text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])

            raw_detections = json.loads(text)

            if isinstance(raw_detections, list):
                for item in raw_detections:
                    if isinstance(item, dict):
                        detections.append(
                            Detection(
                                category="fake_social_proof",
                                element_selector="[itemprop='reviewBody']",
                                confidence=float(item.get("confidence", 0.5)),
                                explanation=str(item.get("explanation", "")),
                                severity=str(item.get("severity", "medium")),  # type: ignore[arg-type]
                                analyzer_name=self.name,
                                platform_context="ecommerce",
                                regulation_refs=["FTC-S5"],
                            )
                        )

        except LLMError:
            logger.exception("Review analyzer LLM call failed")
        except json.JSONDecodeError:
            logger.warning("Review analyzer: could not parse LLM response as JSON")
        except Exception:
            logger.exception("Review analyzer unexpected error")

        return detections
