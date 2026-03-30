"""Tests for the Benchmarking module."""

from __future__ import annotations

import pytest

from core.benchmarking import (
    INDUSTRY_BASELINES,
    CATEGORY_PREVALENCE,
    compute_benchmark,
)
from core.scoring import ScoreBreakdown


def _score(total: float = 50.0, **kw) -> ScoreBreakdown:
    defaults = dict(
        total_score=total,
        pattern_count=5,
        unique_categories=3,
        severity_distribution={"high": 2, "medium": 2, "low": 1},
        highest_severity_category="drip_pricing",
        corroborated_count=1,
        regulation_count=4,
        grade="D",
    )
    defaults.update(kw)
    return ScoreBreakdown(**defaults)


class TestBenchmarking:
    def test_better_than_average(self) -> None:
        # Score of 10 vs ecommerce avg of 52 → better
        result = compute_benchmark(_score(10.0), ["urgency_scarcity"], "ecommerce")
        assert result.percentile_rank == "better"
        assert result.delta < 0

    def test_worse_than_average(self) -> None:
        # Score of 80 vs general avg of 42 → worse
        result = compute_benchmark(_score(80.0), ["drip_pricing"], "general")
        assert result.percentile_rank == "worse"
        assert result.delta > 0

    def test_average_range(self) -> None:
        # Score right at the baseline → average
        baseline = INDUSTRY_BASELINES["saas"]
        result = compute_benchmark(_score(baseline), [], "saas")
        assert result.percentile_rank == "average"

    def test_categories_above_below(self) -> None:
        detected = ["urgency_scarcity", "bnpl_deception"]  # 0.72 vs 0.22 prevalence
        result = compute_benchmark(_score(50.0), detected, "general")
        assert "urgency_scarcity" in result.categories_above_average
        assert "bnpl_deception" in result.categories_below_average

    def test_unknown_platform_falls_back_to_general(self) -> None:
        result = compute_benchmark(_score(50.0), [], "unknown_platform")
        assert result.industry_avg == INDUSTRY_BASELINES["general"]

    def test_all_baselines_have_values(self) -> None:
        for ctx, val in INDUSTRY_BASELINES.items():
            assert 0 < val <= 100, f"Bad baseline for {ctx}: {val}"

    def test_all_prevalences_are_valid(self) -> None:
        for cat, val in CATEGORY_PREVALENCE.items():
            assert 0 < val <= 1.0, f"Bad prevalence for {cat}: {val}"
