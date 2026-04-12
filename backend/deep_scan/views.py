"""
deep_scan/views.py — API endpoint for deep scanning.

POST /api/scans/deep-scan — Run multi-step workflow scan on a URL.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from deep_scan.workflows import WORKFLOWS

logger = logging.getLogger(__name__)


@api_view(["POST"])
def deep_scan_view(request: Request) -> Response:
    """POST /api/scans/deep-scan — Run a deep scan on a URL.

    Request body:
    {
        "url": "https://example.com",
        "workflows": ["search_book", "consent_privacy"]  // optional, defaults to all
    }

    Returns full DeepScanResult with annotated screenshots.
    """
    url = request.data.get("url")
    if not url or not isinstance(url, str):
        return Response(
            {"error": "Missing or invalid 'url' field"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    workflow_ids = request.data.get("workflows")
    if workflow_ids is not None:
        if not isinstance(workflow_ids, list):
            return Response(
                {"error": "'workflows' must be a list of workflow IDs"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Validate workflow IDs
        invalid = [w for w in workflow_ids if w not in WORKFLOWS]
        if invalid:
            return Response(
                {
                    "error": f"Invalid workflow IDs: {invalid}",
                    "available": list(WORKFLOWS.keys()),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    try:
        from deep_scan.service import run_deep_scan_sync

        result = run_deep_scan_sync(url, workflow_ids)
    except Exception as e:
        logger.exception("Deep scan failed for %s", url)
        return Response(
            {"error": f"Deep scan failed: {str(e)[:200]}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Persist scan results
    scan_id = _persist_deep_scan(url, result)
    result.scan_id = scan_id

    return Response(asdict(result), status=status.HTTP_200_OK)


@api_view(["GET"])
def deep_scan_workflows_view(request: Request) -> Response:
    """GET /api/scans/deep-scan/workflows — List available workflows."""
    workflows = {
        wid: {
            "name": w.name,
            "description": w.description,
            "icon": w.icon,
            "step_count": len(w.steps),
        }
        for wid, w in WORKFLOWS.items()
    }
    return Response({"workflows": workflows})


def _persist_deep_scan(url: str, result) -> int | None:
    """Persist deep scan results to the database. Non-fatal."""
    try:
        from scans.models import AuditScan, DetectionRecord

        total_patterns = result.summary.get("total_patterns", 0)
        categories = result.summary.get("categories_found", [])

        scan = AuditScan.objects.create(
            url=url,
            score_total=min(total_patterns * 5, 100),
            score_grade="A" if total_patterns == 0 else (
                "B" if total_patterns < 5 else (
                    "C" if total_patterns < 10 else (
                        "D" if total_patterns < 20 else "F"
                    )
                )
            ),
            pattern_count=total_patterns,
            unique_categories=len(categories),
            corroborated_count=0,
            audit_report={"type": "deep_scan", "summary": result.summary},
        )

        records = []
        for wf in result.workflows:
            for step in wf.steps:
                for det in step.detections:
                    records.append(
                        DetectionRecord(
                            scan=scan,
                            category=det.get("category", ""),
                            element_selector=det.get("element_selector", ""),
                            confidence=det.get("confidence", 0),
                            explanation=det.get("explanation", ""),
                            severity=det.get("severity", "low"),
                            corroborated=det.get("corroborated", False),
                            analyzer_name=det.get("analyzer_name", ""),
                            platform_context=det.get("platform_context", ""),
                            regulation_refs=det.get("regulation_refs", []),
                        )
                    )
        if records:
            DetectionRecord.objects.bulk_create(records)

        return scan.pk
    except Exception:
        logger.exception("Failed to persist deep scan")
        return None
