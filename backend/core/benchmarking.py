"""
core/benchmarking.py — Comparative benchmarking against industry averages.

Stores per-category industry baselines and computes how a site
compares relative to the average.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.scoring import ScoreBreakdown


# Industry average scores by platform context.
# These are calibrated estimates based on dark pattern research.
INDUSTRY_BASELINES: dict[str, float] = {
    "ecommerce": 52.0,
    "saas": 38.0,
    "social_media": 45.0,
    "gaming": 60.0,
    "food_travel": 48.0,
    "fintech": 35.0,
    "consent": 55.0,
    "general": 42.0,
}

# Average category prevalence (% of sites with this pattern)
CATEGORY_PREVALENCE: dict[str, float] = {
    "urgency_scarcity": 0.72,
    "confirmshaming": 0.48,
    "visual_interference": 0.35,
    "preselection": 0.61,
    "hidden_costs": 0.55,
    "misdirection": 0.42,
    "fake_social_proof": 0.38,
    "asymmetric_choice": 0.65,
    "prechecked_consent": 0.58,
    "basket_sneaking": 0.31,
    "drip_pricing": 0.44,
    "roach_motel": 0.52,
    "forced_continuity": 0.46,
    "plan_comparison_trick": 0.29,
    "privacy_zuckering": 0.41,
    "notification_inflation": 0.37,
    "persistent_nagging": 0.33,
    "price_anchoring": 0.56,
    "bnpl_deception": 0.22,
    "intermediate_currency": 0.18,
}


@dataclass
class BenchmarkResult:
    """How a site compares to industry averages."""
    site_score: float
    industry_avg: float
    percentile_rank: str   # "better", "average", "worse"
    delta: float           # site_score - industry_avg
    platform_context: str
    categories_above_average: list[str]
    categories_below_average: list[str]


def compute_benchmark(
    score: ScoreBreakdown,
    detected_categories: list[str],
    platform_context: str = "general",
) -> BenchmarkResult:
    """Compare a site's score against industry baselines.

    Args:
        score: The site's ScoreBreakdown from scoring.py.
        detected_categories: List of category strings detected.
        platform_context: Platform type for baseline selection.

    Returns:
        BenchmarkResult with comparison data.
    """
    baseline = INDUSTRY_BASELINES.get(platform_context, INDUSTRY_BASELINES["general"])
    delta = score.total_score - baseline

    if delta < -10:
        rank = "better"
    elif delta <= 10:
        rank = "average"
    else:
        rank = "worse"

    # Which detected categories are more/less prevalent than average?
    above = []
    below = []
    for cat in detected_categories:
        prevalence = CATEGORY_PREVALENCE.get(cat, 0.5)
        if prevalence >= 0.5:
            above.append(cat)  # Common pattern — site follows the crowd
        else:
            below.append(cat)  # Rare pattern — site is worse than typical

    return BenchmarkResult(
        site_score=score.total_score,
        industry_avg=baseline,
        percentile_rank=rank,
        delta=round(delta, 1),
        platform_context=platform_context,
        categories_above_average=sorted(above),
        categories_below_average=sorted(below),
    )
