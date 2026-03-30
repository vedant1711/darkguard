"""Tests for the scans persistence and API layer."""

from __future__ import annotations

import pytest
from django.test import TestCase

from scans.models import AuditScan, DetectionRecord


@pytest.mark.django_db
class TestAuditScanModel(TestCase):
    def test_create_scan(self) -> None:
        scan = AuditScan.objects.create(
            url="https://example.com",
            score_total=42.5,
            score_grade="C",
            pattern_count=5,
            unique_categories=3,
            corroborated_count=1,
            audit_report={"score": {"total": 42.5}},
        )
        assert scan.pk is not None
        assert scan.score_grade == "C"

    def test_create_detection_record(self) -> None:
        scan = AuditScan.objects.create(url="https://example.com")
        det = DetectionRecord.objects.create(
            scan=scan,
            category="drip_pricing",
            element_selector="div.price",
            confidence=0.9,
            explanation="Hidden fees detected",
            severity="high",
            analyzer_name="checkout_flow",
            regulation_refs=["FTC-S5", "CRD-Art6"],
        )
        assert det.pk is not None
        assert det.scan == scan
        assert scan.detections.count() == 1

    def test_cascade_delete(self) -> None:
        scan = AuditScan.objects.create(url="https://example.com")
        DetectionRecord.objects.create(
            scan=scan,
            category="drip_pricing",
            element_selector="div",
            confidence=0.9,
            explanation="test",
            severity="high",
            analyzer_name="test",
        )
        scan_id = scan.pk
        scan.delete()
        assert DetectionRecord.objects.filter(scan_id=scan_id).count() == 0

    def test_ordering(self) -> None:
        s1 = AuditScan.objects.create(url="https://a.com")
        s2 = AuditScan.objects.create(url="https://b.com")
        scans = list(AuditScan.objects.all())
        # Most recent first
        assert scans[0].pk == s2.pk


@pytest.mark.django_db
class TestScanAPI(TestCase):
    def _create_scan_with_detections(self) -> AuditScan:
        scan = AuditScan.objects.create(
            url="https://example.com/shop",
            score_total=55.0,
            score_grade="D",
            pattern_count=3,
            unique_categories=2,
            corroborated_count=1,
            audit_report={
                "score": {"total": 55.0, "grade": "D"},
                "detections": [],
            },
        )
        DetectionRecord.objects.create(
            scan=scan,
            category="drip_pricing",
            element_selector="div.total",
            confidence=0.95,
            explanation="Hidden shipping fee",
            severity="high",
            analyzer_name="checkout_flow",
        )
        DetectionRecord.objects.create(
            scan=scan,
            category="basket_sneaking",
            element_selector="div.addon",
            confidence=0.8,
            explanation="Insurance auto-added",
            severity="medium",
            analyzer_name="checkout_flow",
        )
        return scan

    def test_scan_list(self) -> None:
        self._create_scan_with_detections()
        resp = self.client.get("/api/scans/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["score_grade"] == "D"

    def test_scan_list_url_filter(self) -> None:
        self._create_scan_with_detections()
        AuditScan.objects.create(url="https://other.com")
        resp = self.client.get("/api/scans/?url=example")
        data = resp.json()
        assert data["total"] == 1

    def test_scan_detail(self) -> None:
        scan = self._create_scan_with_detections()
        resp = self.client.get(f"/api/scans/{scan.pk}/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["detections"]) == 2
        assert data["score_grade"] == "D"

    def test_scan_detail_404(self) -> None:
        resp = self.client.get("/api/scans/99999/")
        assert resp.status_code == 404

    def test_scan_compliance_report(self) -> None:
        scan = self._create_scan_with_detections()
        resp = self.client.get(f"/api/scans/{scan.pk}/report/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"]["total"] == 55.0
