"""Tests for the Report Generator."""

from __future__ import annotations

import pytest

from core.models import Detection
from core.report_generator import generate_audit_report


def _det(
    category: str = "drip_pricing",
    confidence: float = 0.9,
    severity: str = "high",
) -> Detection:
    return Detection(
        category=category,
        element_selector="div",
        confidence=confidence,
        explanation="test explanation",
        severity=severity,
        analyzer_name="test_analyzer",
        regulation_refs=[],
    )


class TestReportGenerator:
    def test_empty_detections_report(self) -> None:
        report = generate_audit_report([], "https://example.com")
        assert report["score"]["total"] == 0.0  # type: ignore[index]
        assert report["score"]["grade"] == "A"  # type: ignore[index]
        assert len(report["detections"]) == 0  # type: ignore[arg-type]

    def test_report_contains_metadata(self) -> None:
        report = generate_audit_report([_det()], "https://example.com")
        meta = report["metadata"]
        assert meta["url"] == "https://example.com"  # type: ignore[index]
        assert "timestamp" in meta  # type: ignore[operator]

    def test_report_contains_scoring(self) -> None:
        report = generate_audit_report([_det()], "https://example.com")
        score = report["score"]
        assert score["total"] > 0  # type: ignore[index]
        assert score["pattern_count"] == 1  # type: ignore[index]
        assert score["grade"] in ("A", "B", "C", "D", "F")  # type: ignore[index]

    def test_report_enriches_regulations(self) -> None:
        report = generate_audit_report([_det(category="drip_pricing")], "https://example.com")
        # drip_pricing should be enriched with FTC-S5 and CRD-Art6
        det = report["detections"][0]  # type: ignore[index]
        assert "FTC-S5" in det["regulation_refs"]
        assert len(report["regulations_violated"]) > 0  # type: ignore[arg-type]

    def test_category_summary_counts(self) -> None:
        dets = [
            _det(category="drip_pricing"),
            _det(category="drip_pricing"),
            _det(category="basket_sneaking"),
        ]
        report = generate_audit_report(dets, "https://example.com")
        summary = report["category_summary"]
        assert summary["drip_pricing"]["count"] == 2  # type: ignore[index]
        assert summary["basket_sneaking"]["count"] == 1  # type: ignore[index]
