"""
core/report_generator.py — Audit Report Generator.

Generates structured audit reports (JSON-serializable dicts) from
detections, scoring, and regulatory analysis.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from core.models import Detection
from core.regulatory_mapper import (
    enrich_regulation_refs,
    get_all_violated_regulations,
)
from core.scoring import ScoreBreakdown, compute_score


def generate_audit_report(
    detections: list[Detection],
    url: str,
) -> dict[str, object]:
    """Build a complete audit report from analyzed detections.

    Returns a JSON-serializable dict containing:
    - score breakdown
    - enriched detections
    - per-category summary
    - violated regulations
    - metadata
    """
    # 1. Enrich with canonical regulation refs
    detections = enrich_regulation_refs(detections)

    # 2. Compute site-wide score
    score = compute_score(detections)

    # 3. Group detections by category
    category_summary: dict[str, dict[str, object]] = {}
    for det in detections:
        if det.category not in category_summary:
            category_summary[det.category] = {
                "count": 0,
                "max_confidence": 0.0,
                "severity": det.severity,
                "regulations": set(),
            }
        entry = category_summary[det.category]
        entry["count"] = int(entry["count"]) + 1  # type: ignore[arg-type]
        entry["max_confidence"] = max(
            float(entry["max_confidence"]),  # type: ignore[arg-type]
            det.confidence,
        )
        entry["regulations"] |= set(det.regulation_refs)  # type: ignore[operator]

    # Convert sets to sorted lists for JSON serialization
    for cat_data in category_summary.values():
        cat_data["regulations"] = sorted(cat_data["regulations"])  # type: ignore[arg-type]

    # 4. Get all violated regulations with full info
    violated_regs = get_all_violated_regulations(detections)

    # 5. Build report
    report: dict[str, object] = {
        "metadata": {
            "url": url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analyzer_version": "1.0.0",
        },
        "score": {
            "total": score.total_score,
            "grade": score.grade,
            "pattern_count": score.pattern_count,
            "unique_categories": score.unique_categories,
            "corroborated_count": score.corroborated_count,
            "severity_distribution": score.severity_distribution,
        },
        "category_summary": category_summary,
        "regulations_violated": [asdict(r) for r in violated_regs],
        "detections": [asdict(d) for d in detections],
    }

    return report
