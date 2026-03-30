"""
core/views.py — POST /api/analyze endpoint.

Accepts the full analysis payload, sanitizes it server-side,
dispatches to all registered analyzers, enriches with regulatory
refs and scoring, persists the result, and returns the audit report.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from core.dispatcher import dispatch
from core.registry import AnalyzerRegistry
from core.regulatory_mapper import enrich_regulation_refs
from core.report_generator import generate_audit_report
from core.sanitizer import sanitize_payload
from core.scoring import compute_score
from core.serializers import AnalyzeRequestSerializer

# Ensure all analyzer packages are discovered on first import
AnalyzerRegistry.discover()


def _persist_scan(
    url: str,
    detections: list,
    report: dict,
    score,
) -> int | None:
    """Persist the scan and its detections to the database.

    Returns the scan ID, or None if persistence fails (non-fatal).
    """
    try:
        from scans.models import AuditScan, DetectionRecord

        scan = AuditScan.objects.create(
            url=url,
            score_total=score.total_score,
            score_grade=score.grade,
            pattern_count=score.pattern_count,
            unique_categories=score.unique_categories,
            corroborated_count=score.corroborated_count,
            audit_report=report,
        )

        records = [
            DetectionRecord(
                scan=scan,
                category=det.category,
                element_selector=det.element_selector,
                confidence=det.confidence,
                explanation=det.explanation,
                severity=det.severity,
                corroborated=det.corroborated,
                analyzer_name=det.analyzer_name,
                platform_context=det.platform_context,
                regulation_refs=det.regulation_refs,
            )
            for det in detections
        ]
        if records:
            DetectionRecord.objects.bulk_create(records)

        return scan.pk
    except Exception:
        # Persistence is non-critical — don't fail the analysis
        import logging
        logging.getLogger(__name__).exception("Failed to persist scan")
        return None


@api_view(["POST"])
def analyze(request: Request) -> Response:
    """POST /api/analyze — run all dark-pattern analyzers."""
    serializer = AnalyzeRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    payload: dict[str, object] = serializer.validated_data  # type: ignore[assignment]

    # Layer 2: server-side PII re-sanitization (defense-in-depth)
    payload = sanitize_payload(payload)

    # Dispatch to all registered analyzers
    detections = asyncio.run(dispatch(payload))

    # Enrich with canonical regulation references
    detections = enrich_regulation_refs(detections)

    # Compute site-wide score
    score = compute_score(detections)

    # Build the full audit report
    url = str(payload.get("url", ""))
    report = generate_audit_report(detections, url)

    # Persist to database (non-blocking, non-fatal)
    scan_id = _persist_scan(url, detections, report, score)

    # Response includes detections, audit report, and scan reference
    response_data = {
        "detections": [asdict(d) for d in detections],
        "audit_report": report,
        "scan_id": scan_id,
    }

    return Response(response_data, status=status.HTTP_200_OK)
