"""
core/regulatory_mapper.py — Maps dark pattern detections to regulatory violations.

Covers:
- FTC Section 5 (US)
- EU DSA Article 25
- GDPR (EU)
- CCPA/CPRA (California)
- ePrivacy Directive
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.models import Detection


@dataclass
class RegulationInfo:
    """Structured regulation reference."""
    code: str
    name: str
    jurisdiction: str
    description: str


# ── Regulatory Database ──────────────────────────────────

REGULATION_DB: dict[str, RegulationInfo] = {
    "FTC-S5": RegulationInfo(
        code="FTC-S5",
        name="FTC Act Section 5",
        jurisdiction="US",
        description="Prohibits unfair or deceptive acts or practices in commerce.",
    ),
    "FTC-DeceptivePricing": RegulationInfo(
        code="FTC-DeceptivePricing",
        name="FTC Guides Against Deceptive Pricing",
        jurisdiction="US",
        description="Prohibits false or misleading pricing representations.",
    ),
    "FTC-NegativeOption": RegulationInfo(
        code="FTC-NegativeOption",
        name="FTC Negative Option Rule",
        jurisdiction="US",
        description="Requires clear disclosure and consent for subscription auto-renewals.",
    ),
    "ROSCA": RegulationInfo(
        code="ROSCA",
        name="Restore Online Shoppers' Confidence Act",
        jurisdiction="US",
        description="Prohibits charging consumers for goods/services without clear consent.",
    ),
    "TILA": RegulationInfo(
        code="TILA",
        name="Truth in Lending Act",
        jurisdiction="US",
        description="Requires clear disclosure of credit terms including APR and fees.",
    ),
    "GDPR-Art7": RegulationInfo(
        code="GDPR-Art7",
        name="GDPR Article 7 — Conditions for Consent",
        jurisdiction="EU",
        description="Consent must be freely given, specific, informed and unambiguous.",
    ),
    "GDPR-Art25": RegulationInfo(
        code="GDPR-Art25",
        name="GDPR Article 25 — Data Protection by Design",
        jurisdiction="EU",
        description="Data protection must be built into processing by default (privacy by default).",
    ),
    "DSA-Art25": RegulationInfo(
        code="DSA-Art25",
        name="EU Digital Services Act Article 25",
        jurisdiction="EU",
        description="Prohibits dark patterns that distort or impair user autonomy or decision-making.",
    ),
    "CRD-Art6": RegulationInfo(
        code="CRD-Art6",
        name="Consumer Rights Directive Article 6",
        jurisdiction="EU",
        description="Requires transparent disclosure of total price including all fees before purchase.",
    ),
    "CRD-Art22": RegulationInfo(
        code="CRD-Art22",
        name="Consumer Rights Directive Article 22",
        jurisdiction="EU",
        description="Prohibits pre-ticked boxes for additional payments; consent must be explicit.",
    ),
    "ePrivacy": RegulationInfo(
        code="ePrivacy",
        name="ePrivacy Directive",
        jurisdiction="EU",
        description="Governs consent requirements for cookies and electronic communications.",
    ),
    "CCPA": RegulationInfo(
        code="CCPA",
        name="California Consumer Privacy Act",
        jurisdiction="US (California)",
        description="Prohibits dark patterns which subvert consumer choices to opt out of data sale.",
    ),
    "UCPD": RegulationInfo(
        code="UCPD",
        name="Unfair Commercial Practices Directive",
        jurisdiction="EU",
        description="Prohibits misleading and aggressive commercial practices.",
    ),
}

# ── Category → Regulation Mapping ────────────────────────

CATEGORY_REGULATION_MAP: dict[str, list[str]] = {
    # Phase 1 categories
    "urgency_scarcity": ["FTC-S5", "DSA-Art25", "UCPD"],
    "confirmshaming": ["FTC-S5", "DSA-Art25"],
    "visual_interference": ["DSA-Art25", "UCPD"],
    "preselection": ["CRD-Art22", "GDPR-Art7"],
    "hidden_costs": ["FTC-S5", "CRD-Art6"],
    "misdirection": ["FTC-S5", "DSA-Art25", "UCPD"],
    "fake_social_proof": ["FTC-S5", "UCPD"],
    # Phase 2 — consent
    "asymmetric_choice": ["GDPR-Art7", "ePrivacy", "DSA-Art25"],
    "prechecked_consent": ["GDPR-Art7", "ePrivacy", "CRD-Art22"],
    # Phase 2 — checkout
    "basket_sneaking": ["FTC-S5", "CRD-Art22"],
    "drip_pricing": ["FTC-S5", "CRD-Art6"],
    # Phase 2 — subscription
    "roach_motel": ["FTC-NegativeOption", "FTC-S5", "DSA-Art25"],
    "forced_continuity": ["ROSCA", "FTC-NegativeOption"],
    "plan_comparison_trick": ["FTC-S5", "DSA-Art25"],
    # Phase 2 — privacy
    "privacy_zuckering": ["GDPR-Art25", "CCPA"],
    # Phase 2 — nagging
    "notification_inflation": ["GDPR-Art7", "ePrivacy"],
    "persistent_nagging": ["FTC-S5", "DSA-Art25"],
    # Phase 2 — pricing
    "price_anchoring": ["FTC-DeceptivePricing", "FTC-S5"],
    "bnpl_deception": ["TILA", "FTC-S5"],
    "intermediate_currency": ["DSA-Art25", "FTC-S5"],
    # Phase 6 — deceptive.design taxonomy additions
    "trick_wording": ["FTC-S5", "UCPD", "DSA-Art25"],
    "forced_action": ["GDPR-Art7", "DSA-Art25"],
    "disguised_ads": ["FTC-S5", "DSA-Art25", "UCPD"],
    "comparison_prevention": ["UCPD", "CRD-Art6", "DSA-Art25"],
    "obstruction": ["DSA-Art25", "FTC-NegativeOption", "FTC-S5"],
}


def enrich_regulation_refs(detections: list[Detection]) -> list[Detection]:
    """Enrich detections with regulation references from the canonical mapping.

    If the analyzer already set some refs, merge them with the canonical set.
    """
    for det in detections:
        canonical_refs = CATEGORY_REGULATION_MAP.get(det.category, [])
        existing = set(det.regulation_refs)
        merged = list(existing | set(canonical_refs))
        det.regulation_refs = sorted(merged)
    return detections


def get_regulation_info(code: str) -> RegulationInfo | None:
    """Look up structured regulation data by code."""
    return REGULATION_DB.get(code)


def get_all_violated_regulations(detections: list[Detection]) -> list[RegulationInfo]:
    """Extract a unique list of all violated regulations from a set of detections."""
    codes: set[str] = set()
    for det in detections:
        codes.update(det.regulation_refs)
    
    return [REGULATION_DB[c] for c in sorted(codes) if c in REGULATION_DB]
