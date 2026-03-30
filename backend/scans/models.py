"""
scans/models.py — Django ORM models for audit scan persistence.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class AuditScan(models.Model):
    """A single audit scan of a URL."""

    url = models.URLField(max_length=2048, db_index=True)
    scanned_at = models.DateTimeField(default=timezone.now, db_index=True)

    # Scoring
    score_total = models.FloatField(default=0.0)
    score_grade = models.CharField(max_length=2, default="A")
    pattern_count = models.IntegerField(default=0)
    unique_categories = models.IntegerField(default=0)
    corroborated_count = models.IntegerField(default=0)

    # Full audit report (JSON blob)
    audit_report = models.JSONField(default=dict)

    class Meta:
        ordering = ["-scanned_at"]
        indexes = [
            models.Index(fields=["url", "-scanned_at"]),
        ]

    def __str__(self) -> str:
        return f"Scan {self.pk}: {self.url} ({self.score_grade}, {self.scanned_at:%Y-%m-%d})"


class DetectionRecord(models.Model):
    """A persisted dark pattern detection tied to an AuditScan."""

    scan = models.ForeignKey(
        AuditScan,
        on_delete=models.CASCADE,
        related_name="detections",
    )
    category = models.CharField(max_length=64, db_index=True)
    element_selector = models.TextField()
    confidence = models.FloatField()
    explanation = models.TextField()
    severity = models.CharField(max_length=10)
    corroborated = models.BooleanField(default=False)
    analyzer_name = models.CharField(max_length=64)
    platform_context = models.CharField(max_length=64, default="general")
    regulation_refs = models.JSONField(default=list)

    class Meta:
        ordering = ["-confidence"]

    def __str__(self) -> str:
        return f"{self.category} ({self.confidence:.0%}) on {self.element_selector[:40]}"
