"""
scans/views.py — REST API views for scan history and compliance reports.

Endpoints:
- GET /api/scans/               → paginated scan history
- GET /api/scans/<id>/          → single scan detail with detections
- GET /api/scans/<id>/report/   → compliance report for a scan
"""

from __future__ import annotations

from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from scans.models import AuditScan, DetectionRecord


@api_view(["GET"])
def scan_list(request: Request) -> Response:
    """GET /api/scans/ — Paginated scan history.

    Query params:
        ?url=...     Filter by URL (substring match)
        ?limit=N     Number of results (default: 20, max: 100)
        ?offset=N    Pagination offset (default: 0)
    """
    url_filter = request.query_params.get("url", "")
    limit = min(int(request.query_params.get("limit", "20")), 100)
    offset = int(request.query_params.get("offset", "0"))

    qs = AuditScan.objects.all()
    if url_filter:
        qs = qs.filter(url__icontains=url_filter)

    total = qs.count()
    scans = qs[offset: offset + limit]

    data = {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [
            {
                "id": scan.pk,
                "url": scan.url,
                "scanned_at": scan.scanned_at.isoformat(),
                "score_total": scan.score_total,
                "score_grade": scan.score_grade,
                "pattern_count": scan.pattern_count,
                "unique_categories": scan.unique_categories,
                "corroborated_count": scan.corroborated_count,
            }
            for scan in scans
        ],
    }
    return Response(data)


@api_view(["GET"])
def scan_detail(request: Request, scan_id: int) -> Response:
    """GET /api/scans/<id>/ — Single scan detail with all detections."""
    try:
        scan = AuditScan.objects.get(pk=scan_id)
    except AuditScan.DoesNotExist:
        return Response(
            {"error": "Scan not found"}, status=status.HTTP_404_NOT_FOUND
        )

    detections = scan.detections.all()  # type: ignore[attr-defined]

    data = {
        "id": scan.pk,
        "url": scan.url,
        "scanned_at": scan.scanned_at.isoformat(),
        "score_total": scan.score_total,
        "score_grade": scan.score_grade,
        "pattern_count": scan.pattern_count,
        "unique_categories": scan.unique_categories,
        "corroborated_count": scan.corroborated_count,
        "detections": [
            {
                "id": det.pk,
                "category": det.category,
                "element_selector": det.element_selector,
                "confidence": det.confidence,
                "explanation": det.explanation,
                "severity": det.severity,
                "corroborated": det.corroborated,
                "analyzer_name": det.analyzer_name,
                "platform_context": det.platform_context,
                "regulation_refs": det.regulation_refs,
            }
            for det in detections
        ],
    }
    return Response(data)


@api_view(["GET"])
def scan_compliance_report(request: Request, scan_id: int) -> Response:
    """GET /api/scans/<id>/report/ — Full compliance audit report (JSON)."""
    try:
        scan = AuditScan.objects.get(pk=scan_id)
    except AuditScan.DoesNotExist:
        return Response(
            {"error": "Scan not found"}, status=status.HTTP_404_NOT_FOUND
        )

    # The full report was persisted during the scan
    return Response(scan.audit_report)
