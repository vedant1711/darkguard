"""
scans/crawler_views.py — Server-side URL scan endpoint using Playwright.

POST /api/scans/crawl — Accepts a URL, crawls it headlessly,
runs all analyzers, and returns the full audit report.
"""

from __future__ import annotations

import asyncio
import logging
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
from core.benchmarking import compute_benchmark

logger = logging.getLogger(__name__)

AnalyzerRegistry.discover()


@api_view(["POST"])
def crawl_and_analyze(request: Request) -> Response:
    """POST /api/scans/crawl — Crawl a URL and analyze for dark patterns.

    Request body: { "url": "https://example.com" }
    """
    url = request.data.get("url")
    if not url or not isinstance(url, str):
        return Response(
            {"error": "Missing or invalid 'url' field"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 1. Crawl the URL (with graceful fallback if Playwright unavailable)
    crawl_available = False
    try:
        from crawler.service import crawl_url_sync
        result = crawl_url_sync(url)
        crawl_available = True
        payload: dict[str, object] = {
            "dom_metadata": result.dom_metadata,
            "text_content": result.text_content,
            "screenshot_b64": result.screenshot_b64,
            "review_text": result.review_text,
            "checkout_flow": result.checkout_flow,
            "nagging_events": result.nagging_events,
            "url": url,
        }
    except Exception as e:
        logger.warning("Crawl unavailable for %s (%s) — using minimal payload", url, e)
        # Fallback: run LLM-based analyzers with just the URL
        payload = {
            "dom_metadata": {
                "hidden_elements": [],
                "interactive_elements": [],
                "prechecked_inputs": [],
                "url": url,
            },
            "text_content": {"button_labels": [], "headings": [], "body_text": ""},
            "screenshot_b64": "",
            "review_text": None,
            "checkout_flow": None,
            "nagging_events": None,
            "url": url,
        }

    # 3. Sanitize
    payload = sanitize_payload(payload)

    # 4. Dispatch to analyzers
    detections = asyncio.run(dispatch(payload))

    # 5. Enrich + score
    detections = enrich_regulation_refs(detections)
    score = compute_score(detections)
    report = generate_audit_report(detections, url)

    # 6. Benchmark
    detected_categories = list({d.category for d in detections})
    benchmark = compute_benchmark(score, detected_categories)

    # 7. Persist
    scan_id = None
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
        scan_id = scan.pk
    except Exception:
        logger.exception("Failed to persist crawl scan")

    return Response(
        {
            "detections": [asdict(d) for d in detections],
            "audit_report": report,
            "scan_id": scan_id,
            "benchmark": asdict(benchmark),
            "crawl_available": crawl_available,
        },
        status=status.HTTP_200_OK,
    )
