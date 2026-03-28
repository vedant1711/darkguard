"""
checkout_flow_analyzer/service.py — Checkout Flow Analyzer Service.

Detects:
- Drip Pricing: Unavoidable fees revealed only at the end of the checkout process.
- Basket Sneaking: Non-essential items (e.g., insurance) automatically added to the cart.
"""

from __future__ import annotations

from checkout_flow_analyzer.interfaces import CheckoutItem, CheckoutPayload
from core.interfaces import BaseAnalyzer
from core.models import Detection


class CheckoutFlowAnalyzerService(BaseAnalyzer):
    """Analyzes the checkout flow for unexpected costs and items."""

    @property
    def name(self) -> str:
        return "checkout_flow"

    @property
    def required_payload_keys(self) -> list[str]:
        return ["checkout_flow"]

    async def analyze(self, payload: dict[str, object]) -> list[Detection]:
        detections: list[Detection] = []

        val = self._parse_payload(payload)
        if not val:
            return detections

        detections.extend(self._check_basket_sneaking(val.items))
        detections.extend(self._check_drip_pricing(val))

        return detections

    def _parse_payload(self, payload: dict[str, object]) -> CheckoutPayload | None:
        """Extract checkout data from raw payload."""
        checkout_data = payload.get("checkout_flow")
        if not isinstance(checkout_data, dict):
            return None

        # Parse prices safely
        try:
            adv_price_raw = checkout_data.get("advertised_price")
            adv_price = float(adv_price_raw) if adv_price_raw is not None else None
        except (ValueError, TypeError):
            adv_price = None

        try:
            fin_price_raw = checkout_data.get("final_price")
            fin_price = float(fin_price_raw) if fin_price_raw is not None else 0.0
        except (ValueError, TypeError):
            fin_price = 0.0

        raw_items = checkout_data.get("items", [])
        parsed_items: list[CheckoutItem] = []
        
        if isinstance(raw_items, list):
            for it in raw_items:
                if not isinstance(it, dict):
                    continue
                try:
                    price = float(it.get("price", 0.0))
                except (ValueError, TypeError):
                    price = 0.0

                parsed_items.append(
                    CheckoutItem(
                        name=str(it.get("name", "Unknown Item")),
                        price=price,
                        is_user_added=bool(it.get("is_user_added", True)),
                        item_type=str(it.get("item_type", "product")).lower(),
                    )
                )

        return CheckoutPayload(
            advertised_price=adv_price,
            final_price=fin_price,
            items=parsed_items,
        )

    def _check_basket_sneaking(self, items: list[CheckoutItem]) -> list[Detection]:
        """Flag items added to the cart without user consent."""
        detections: list[Detection] = []
        for item in items:
            # If it's an addon or product not added by the user, and it costs money
            if not item.is_user_added and item.item_type in ("addon", "product") and item.price > 0:
                detections.append(
                    Detection(
                        category="basket_sneaking",
                        element_selector="checkout-item-list",
                        confidence=0.95,
                        explanation=(
                            f"The item '{item.name}' costing {item.price:.2f} was automatically "
                            "added to your cart without explicit consent."
                        ),
                        severity="high",
                        analyzer_name=self.name,
                        platform_context="ecommerce",
                        regulation_refs=["FTC-S5", "CRD-Art22"],
                    )
                )
        return detections

    def _check_drip_pricing(self, payload: CheckoutPayload) -> list[Detection]:
        """Flag unavoidable fees revealed only at final checkout stage."""
        detections: list[Detection] = []
        
        suspect_fees = [
            it for it in payload.items 
            if it.item_type == "fee" and ("service" in it.name.lower() or "convenience" in it.name.lower() or "booking" in it.name.lower())
        ]

        if payload.advertised_price is not None and suspect_fees:
            # Verify if these fees caused a price jump
            total_fees = sum(f.price for f in suspect_fees)
            if total_fees > 0:
                fee_names = ", ".join(f.name for f in suspect_fees)
                detections.append(
                    Detection(
                        category="drip_pricing",
                        element_selector="checkout-fee-list",
                        confidence=0.9,
                        explanation=(
                            f"Hidden fees ({fee_names} totaling {total_fees:.2f}) "
                            f"were added at the final checkout step, inflating the "
                            f"advertised price of {payload.advertised_price:.2f}."
                        ),
                        severity="high",
                        analyzer_name=self.name,
                        platform_context="ecommerce",
                        regulation_refs=["FTC-S5", "CRD-Art6"],
                    )
                )
        return detections
