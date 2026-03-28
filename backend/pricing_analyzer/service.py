"""
pricing_analyzer/service.py — Pricing Analyzer Service.

Uses model-agnostic LLM client for text classification to detect:
- Price Anchoring (fake discounts)
- BNPL Deception (hidden costs in Buy Now Pay Later)
- Intermediate Currency (using gems/coins to obscure real cost)
"""

from __future__ import annotations

import json
import logging

from core.interfaces import BaseAnalyzer
from core.llm_client import get_llm_client
from core.models import Detection
from core.sanitizer import sanitize_text
from pricing_analyzer.interfaces import PricingPayload

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """
Analyze the following text extracted from a product pricing or checkout page.
Determine if any of the following pricing Dark Patterns are present:
1. "price_anchoring": Showing an artificially inflated, highly unrealistic original price crossed out next to a "sale" price to make it seem like an incredible deal.
2. "bnpl_deception": "Buy Now Pay Later" options pushed aggressively (e.g., highlighting small monthly payments) without clear disclosure of interest rates or the total long-term cost.
3. "intermediate_currency": Using fake virtual currencies (e.g., "coins", "gems", "credits") instead of real money to obscure the actual monetary cost, forcing users to buy bundles.

Respond ONLY with a valid JSON array of objects. Do not include markdown formatting like ```json.
If no dark patterns are found, return an empty array: []

Each object must have exactly these keys:
- "category": string (must be one of: "price_anchoring", "bnpl_deception", "intermediate_currency")
- "confidence": float between 0.0 and 1.0 (how certain you are)
- "explanation": string (brief explanation of the deceptive practice based on the text)

Text Data:
{text_data}
"""


class PricingAnalyzerService(BaseAnalyzer):
    """LLM-backed analyzer for deceptive pricing strategies."""

    @property
    def name(self) -> str:
        return "pricing"

    @property
    def required_payload_keys(self) -> list[str]:
        # Uses text_content for LLM evaluation of pricing tricks
        return ["text_content"]

    async def analyze(self, payload: dict[str, object]) -> list[Detection]:
        detections: list[Detection] = []
        
        val = self._parse_payload(payload)
        if not val or len(val.body_text) < 10:
            return detections
            
        safe_text = sanitize_text(val.body_text)

        # Get the LLM client configured for text classification
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
                if cat not in ("price_anchoring", "bnpl_deception", "intermediate_currency"):
                    continue
                    
                conf_val = res.get("confidence", 0.0)
                try:
                    conf = float(conf_val)
                    conf = max(0.0, min(1.0, conf))
                except (ValueError, TypeError):
                    conf = 0.5
                    
                explanation = str(res.get("explanation", ""))
                
                refs = ["FTC-S5"]
                if cat == "price_anchoring":
                    refs.append("FTC-DeceptivePricing")
                elif cat == "bnpl_deception":
                    refs.append("TILA") # Truth in Lending Act
                elif cat == "intermediate_currency":
                    refs.append("DSA-Art25")
                
                detections.append(
                    Detection(
                        category=cat,
                        element_selector="document",
                        confidence=conf,
                        explanation=explanation,
                        severity="medium",
                        analyzer_name=self.name,
                        platform_context="ecommerce_or_gaming",
                        regulation_refs=refs,
                    )
                )

        except (json.JSONDecodeError, Exception) as e:
            logger.error("LLM evaluation failed in PricingAnalyzer: %s", e)

        return detections

    def _parse_payload(self, payload: dict[str, object]) -> PricingPayload | None:
        """Extract text data from payload for analysis."""
        text_data = payload.get("text_content")
        if not isinstance(text_data, dict):
            return None

        body = str(text_data.get("body_text", ""))
        
        # Pull text from headings and interactive elements if they exist
        raw_headings = text_data.get("headings", [])
        if isinstance(raw_headings, list):
            for h in raw_headings:
                if isinstance(h, str):
                    body += f"\n{h}"
        
        url = str(payload.get("url", ""))

        return PricingPayload(url=url, body_text=body)
