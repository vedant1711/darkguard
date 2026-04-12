"""scans/urls.py — URL routing for the scan history API."""

from django.urls import path

from scans.views import scan_list, scan_detail, scan_compliance_report
from scans.crawler_views import crawl_and_analyze
from scans.pdf_views import scan_pdf_report
from deep_scan.views import deep_scan_view, deep_scan_workflows_view

urlpatterns = [
    path("", scan_list, name="scan-list"),
    path("crawl", crawl_and_analyze, name="crawl-and-analyze"),
    path("deep-scan", deep_scan_view, name="deep-scan"),
    path("deep-scan/workflows", deep_scan_workflows_view, name="deep-scan-workflows"),
    path("<int:scan_id>/", scan_detail, name="scan-detail"),
    path("<int:scan_id>/report/", scan_compliance_report, name="scan-report"),
    path("<int:scan_id>/report/pdf", scan_pdf_report, name="scan-report-pdf"),
]
