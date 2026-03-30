"""Tests for the Regulatory Mapper."""

from __future__ import annotations

import pytest

from core.models import Detection
from core.regulatory_mapper import (
    CATEGORY_REGULATION_MAP,
    REGULATION_DB,
    enrich_regulation_refs,
    get_all_violated_regulations,
    get_regulation_info,
)


def _det(
    category: str = "urgency_scarcity",
    regulation_refs: list[str] | None = None,
) -> Detection:
    return Detection(
        category=category,
        element_selector="div",
        confidence=0.9,
        explanation="test",
        severity="high",
        analyzer_name="test",
        regulation_refs=regulation_refs or [],
    )


class TestRegulatoryMapper:
    def test_enrich_adds_canonical_refs(self) -> None:
        det = _det(category="drip_pricing", regulation_refs=[])
        enrich_regulation_refs([det])
        assert "FTC-S5" in det.regulation_refs
        assert "CRD-Art6" in det.regulation_refs

    def test_enrich_merges_existing_refs(self) -> None:
        det = _det(category="drip_pricing", regulation_refs=["CUSTOM-REF"])
        enrich_regulation_refs([det])
        assert "CUSTOM-REF" in det.regulation_refs
        assert "FTC-S5" in det.regulation_refs

    def test_enrich_preserves_unknown_categories(self) -> None:
        det = _det(category="unknown_pattern", regulation_refs=["MY-REF"])
        enrich_regulation_refs([det])
        # Should keep existing ref, not crash
        assert det.regulation_refs == ["MY-REF"]

    def test_get_regulation_info_known(self) -> None:
        info = get_regulation_info("GDPR-Art7")
        assert info is not None
        assert info.jurisdiction == "EU"
        assert "consent" in info.description.lower()

    def test_get_regulation_info_unknown(self) -> None:
        assert get_regulation_info("FAKE-LAW") is None

    def test_get_all_violated_regulations(self) -> None:
        dets = [
            _det(category="drip_pricing"),
            _det(category="privacy_zuckering"),
        ]
        enrich_regulation_refs(dets)
        violated = get_all_violated_regulations(dets)
        codes = [v.code for v in violated]
        assert "FTC-S5" in codes
        assert "GDPR-Art25" in codes

    def test_all_categories_have_mappings(self) -> None:
        # Verify that every key in the mapping exists
        for cat, refs in CATEGORY_REGULATION_MAP.items():
            assert len(refs) > 0, f"Category {cat} has no regulation refs"
            for ref in refs:
                assert ref in REGULATION_DB, f"Regulation {ref} in {cat} not found in DB"
