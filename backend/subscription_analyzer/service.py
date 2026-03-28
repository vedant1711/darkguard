"""
subscription_analyzer/service.py — Subscription Analyzer Service.

Uses model-agnostic LLM client for text classification to detect:
- Roach motel (hard to cancel)
- Forced continuity (hidden auto-renewals / free trial traps)
- Plan comparison tricks
"""

from __future__ import annotations

import json
import logging

from core.interfaces import BaseAnalyzer
from core.llm_client import get_llm_client
from core.models import Detection
from core.sanitizer import sanitize_text
from subscription_analyzer.interfaces import SubscriptionPayload

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """
Analyze the following text extracted from a subscription or pricing page.
Determine if any of the following Dark Patterns are present:
1. "roach_motel": Extremely difficult to cancel (e.g., must call a phone number during specific hours to cancel an online subscription) or cancellation info is deliberately obfuscated.
2. "forced_continuity": A "free trial" that automatically converts to a paid, recurring subscription without clear, prominent disclosure of the terms, or annual billed-upfront plans masquerading as monthly plans.
3. "plan_comparison_trick": Deceptive presentation of tiers (e.g., hiding the basic plan, or presenting the most expensive plan as the only logical choice via manipulative copy).

Respond ONLY with a valid JSON array of objects. Do not include markdown formatting like ```json.
If no dark patterns are found, return an empty array: []

Each object must have exactly these keys:
- "category": string (must be one of: "roach_motel", "forced_continuity", "plan_comparison_trick")
- "confidence": float between 0.0 and 1.0 (how certain you are)
- "explanation": string (brief explanation of the deceptive practice based on the text)

Text Data:
{text_data}
"""


class SubscriptionAnalyzerService(BaseAnalyzer):
    """LLM-backed analyzer for subscription dark patterns."""

    @property
    def name(self) -> str:
        return "subscription"

    @property
    def required_payload_keys(self) -> list[str]:
        # Uses text_content to evaluate the terms and dom_metadata conceptually,
        # but we primarily rely on text_content for LLM classification.
        return ["text_content"]

    async def analyze(self, payload: dict[str, object]) -> list[Detection]:
        detections: list[Detection] = []
        
        val = self._parse_payload(payload)
        if not val or not val.body_text:
            return detections

        # Construct the text to analyze
        parts = []
        if val.headings:
            parts.append("Headings:\n" + "\n".join(val.headings))
        if val.buttons:
            parts.append("Buttons:\n" + "\n".join(val.buttons))
        parts.append("Body Text:\n" + val.body_text)

        combined_text = "\n\n".join(parts)
        
        # ACTIVE RE-REDACTION (Layer 3) before sending to LLM
        safe_text = sanitize_text(combined_text)

        # Get the LLM client configured for text classification (will use NIM if available, else Gemini)
        llm = get_llm_client(purpose="text_classification")

        prompt = PROMPT_TEMPLATE.format(text_data=safe_text)
        
        try:
            response_text = await llm.generate(prompt)
            # Clean up potential markdown formatting from LLM response
            cleaned_resp = response_text.strip()
            if cleaned_resp.startswith("```json"):
                cleaned_resp = cleaned_resp[7:]
            if cleaned_resp.startswith("```"):
                cleaned_resp = cleaned_resp[3:]
            if cleaned_resp.endswith("```"):
                cleaned_resp = cleaned_resp[:-3]
            
            results = json.loads(cleaned_resp.strip())
            
            if not isinstance(results, list):
                return detections
                
            for res in results:
                if not isinstance(res, dict):
                    continue
                
                cat = res.get("category", "")
                if cat not in ("roach_motel", "forced_continuity", "plan_comparison_trick"):
                    continue
                    
                conf_val = res.get("confidence", 0.0)
                try:
                    conf = float(conf_val)
                    conf = max(0.0, min(1.0, conf))
                except (ValueError, TypeError):
                    conf = 0.5
                    
                explanation = str(res.get("explanation", ""))
                
                # Assign appropriate regulation based on category
                refs = ["FTC-S5"]
                if cat == "forced_continuity":
                    refs.append("ROSCA") # Restore Online Shoppers' Confidence Act
                elif cat == "roach_motel":
                    refs.append("FTC-NegativeOption")
                
                detections.append(
                    Detection(
                        category=cat,
                        element_selector="document",
                        confidence=conf,
                        explanation=explanation,
                        severity="high" if cat in ("roach_motel", "forced_continuity") else "medium",
                        analyzer_name=self.name,
                        platform_context="subscription",
                        regulation_refs=refs,
                    )
                )

        except (json.JSONDecodeError, Exception) as e:
            logger.error("LLM evaluation failed in SubscriptionAnalyzer: %s", e)

        return detections

    def _parse_payload(self, payload: dict[str, object]) -> SubscriptionPayload | None:
        """Extract text content from the payload."""
        text_data = payload.get("text_content")
        if not isinstance(text_data, dict):
            return None

        body = str(text_data.get("body_text", ""))
        
        raw_headings = text_data.get("headings", [])
        headings = [str(h) for h in raw_headings] if isinstance(raw_headings, list) else []
        
        raw_buttons = text_data.get("button_labels", [])
        buttons = []
        if isinstance(raw_buttons, list):
            for b in raw_buttons:
                if isinstance(b, dict):
                    buttons.append(str(b.get("text", "")))
                elif isinstance(b, str):
                    buttons.append(b)
        
        # Don't bother analyzing if there's hardly any text
        if len(body) < 20 and not headings and not buttons:
            return None

        return SubscriptionPayload(
            url=str(payload.get("url", "")),
            body_text=body,
            headings=headings,
            buttons=buttons,
        )
