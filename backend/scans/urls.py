"""scans/urls.py — URL routing for the scan history API."""

from django.urls import path

from scans.views import scan_list, scan_detail, scan_compliance_report

urlpatterns = [
    path("", scan_list, name="scan-list"),
    path("<int:scan_id>/", scan_detail, name="scan-detail"),
    path("<int:scan_id>/report/", scan_compliance_report, name="scan-report"),
]
