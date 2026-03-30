"""
core/scoring.py — Dark Pattern Scoring Engine.

Computes a site-wide "Dark Pattern Score" (0-100) from a set of detections.
Higher score = more deceptive. Incorporates:
- Pattern count and diversity
- Severity weighting
- Corroboration bonus
- Platform context weighting
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.models import Detection


# ── Severity Weights ─────────────────────────────────────

SEVERITY_WEIGHT: dict[str, float] = {
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
}

# Corroboration multiplier (2+ analyzers agreed)
CORROBORATION_BONUS = 1.5

# Maximum raw score before normalization (approx. 10 high-severity corroborated patterns)
MAX_RAW_SCORE = 45.0


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of the dark pattern score."""
    total_score: float
    pattern_count: int
    unique_categories: int
    severity_distribution: dict[str, int]
    highest_severity_category: str
    corroborated_count: int
    regulation_count: int
    grade: str  # A-F


def _compute_grade(score: float) -> str:
    """Map a 0-100 score to a letter grade (A = clean, F = severe)."""
    if score <= 10:
        return "A"
    elif score <= 25:
        return "B"
    elif score <= 45:
        return "C"
    elif score <= 65:
        return "D"
    else:
        return "F"


def compute_score(detections: list[Detection]) -> ScoreBreakdown:
    """Compute a site-wide Dark Pattern Score from the given detections.

    Scoring formula:
        raw_score = Σ (severity_weight × confidence × corroboration_bonus)
        normalized_score = min(100, (raw_score / MAX_RAW_SCORE) × 100)
    
    Additional factors:
        - Category diversity bonus: +2 per unique category beyond the first
    """
    if not detections:
        return ScoreBreakdown(
            total_score=0.0,
            pattern_count=0,
            unique_categories=0,
            severity_distribution={"high": 0, "medium": 0, "low": 0},
            highest_severity_category="",
            corroborated_count=0,
            regulation_count=0,
            grade="A",
        )

    raw = 0.0
    categories: set[str] = set()
    sev_dist: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    corr_count = 0
    all_regs: set[str] = set()
    highest_sev_cat = ""
    highest_sev_val = 0.0

    for det in detections:
        weight = SEVERITY_WEIGHT.get(det.severity, 1.0)
        multiplier = CORROBORATION_BONUS if det.corroborated else 1.0
        contribution = weight * det.confidence * multiplier
        raw += contribution

        categories.add(det.category)
        sev_dist[det.severity] = sev_dist.get(det.severity, 0) + 1
        all_regs.update(det.regulation_refs)

        if det.corroborated:
            corr_count += 1

        if contribution > highest_sev_val:
            highest_sev_val = contribution
            highest_sev_cat = det.category

    # Category diversity bonus
    diversity_bonus = max(0, (len(categories) - 1)) * 2.0
    raw += diversity_bonus

    # Normalize to 0-100
    normalized = min(100.0, (raw / MAX_RAW_SCORE) * 100.0)
    normalized = round(normalized, 1)

    return ScoreBreakdown(
        total_score=normalized,
        pattern_count=len(detections),
        unique_categories=len(categories),
        severity_distribution=sev_dist,
        highest_severity_category=highest_sev_cat,
        corroborated_count=corr_count,
        regulation_count=len(all_regs),
        grade=_compute_grade(normalized),
    )
