"""Tests for the Scoring Engine."""

from __future__ import annotations

import pytest

from core.models import Detection
from core.scoring import ScoreBreakdown, compute_score


def _det(
    category: str = "urgency_scarcity",
    confidence: float = 0.9,
    severity: str = "high",
    corroborated: bool = False,
) -> Detection:
    return Detection(
        category=category,
        element_selector="div",
        confidence=confidence,
        explanation="test",
        severity=severity,
        corroborated=corroborated,
        analyzer_name="test",
        regulation_refs=["FTC-S5"],
    )


class TestScoringEngine:
    def test_empty_detections_returns_grade_a(self) -> None:
        result = compute_score([])
        assert result.total_score == 0.0
        assert result.grade == "A"
        assert result.pattern_count == 0

    def test_single_high_severity_detection(self) -> None:
        result = compute_score([_det(severity="high", confidence=0.9)])
        assert result.total_score > 0
        assert result.pattern_count == 1
        assert result.severity_distribution["high"] == 1

    def test_corroboration_increases_score(self) -> None:
        score_without = compute_score([_det(corroborated=False)])
        score_with = compute_score([_det(corroborated=True)])
        assert score_with.total_score > score_without.total_score

    def test_category_diversity_bonus(self) -> None:
        # Two different categories should score higher than two of the same
        same = compute_score([
            _det(category="urgency_scarcity"),
            _det(category="urgency_scarcity"),
        ])
        diverse = compute_score([
            _det(category="urgency_scarcity"),
            _det(category="confirmshaming"),
        ])
        assert diverse.total_score > same.total_score
        assert diverse.unique_categories == 2

    def test_max_score_is_100(self) -> None:
        # A massive number of high-severity patterns should cap at 100
        many = [_det(severity="high", confidence=1.0, corroborated=True) for _ in range(50)]
        result = compute_score(many)
        assert result.total_score <= 100.0

    def test_grade_mapping(self) -> None:
        # Low score = good grade
        low = compute_score([_det(severity="low", confidence=0.1)])
        assert low.grade in ("A", "B")

        # Many high patterns = bad grade
        high = compute_score([
            _det(severity="high", confidence=1.0, category=f"cat_{i}")
            for i in range(10)
        ])
        assert high.grade in ("D", "F")
