"""
scans/pdf_views.py — HTML compliance report export.

Generates a styled HTML compliance report that can be saved as PDF
via the browser's print functionality.
"""

from __future__ import annotations

from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework import status

from scans.models import AuditScan


def _grade_color(grade: str) -> str:
    colors = {
        "A": "#2ed573", "B": "#7bed9f", "C": "#ffa502",
        "D": "#ff6348", "F": "#ff4757",
    }
    return colors.get(grade, "#888")


def _severity_color(sev: str) -> str:
    return {"high": "#ff4757", "medium": "#ffa502", "low": "#3498db"}.get(sev, "#888")


@api_view(["GET"])
def scan_pdf_report(request: Request, scan_id: int) -> HttpResponse:
    """GET /api/scans/<id>/report/pdf — Styled HTML compliance report."""
    try:
        scan = AuditScan.objects.get(pk=scan_id)
    except AuditScan.DoesNotExist:
        return HttpResponse("Scan not found", status=404)

    report = scan.audit_report
    score = report.get("score", {})
    grade = score.get("grade", "?")
    detections = scan.detections.all()
    regs = report.get("regulations_violated", [])
    cat_summary = report.get("category_summary", {})

    # Build the HTML
    det_rows = ""
    for det in detections:
        reg_badges = " ".join(
            f'<span class="reg">{r}</span>' for r in (det.regulation_refs or [])
        )
        det_rows += f"""
        <tr>
            <td><strong>{det.category.replace('_', ' ').title()}</strong></td>
            <td><span class="sev" style="background:{_severity_color(det.severity)}20;color:{_severity_color(det.severity)}">{det.severity.upper()}</span></td>
            <td>{det.confidence:.0%}</td>
            <td>{det.explanation}</td>
            <td>{det.analyzer_name}</td>
            <td>{reg_badges}</td>
        </tr>
        """

    reg_rows = ""
    for reg in regs:
        reg_rows += f"""
        <tr>
            <td><span class="reg">{reg.get('code','')}</span></td>
            <td><strong>{reg.get('name','')}</strong></td>
            <td>{reg.get('jurisdiction','')}</td>
            <td>{reg.get('description','')}</td>
        </tr>
        """

    cat_rows = ""
    for cat_name, data in cat_summary.items():
        cat_rows += f"""
        <tr>
            <td><strong>{cat_name.replace('_', ' ').title()}</strong></td>
            <td>{data.get('count', 0)}</td>
            <td><span class="sev" style="background:{_severity_color(str(data.get('severity','low')))}20;color:{_severity_color(str(data.get('severity','low')))}">{str(data.get('severity','')).upper()}</span></td>
            <td>{float(data.get('max_confidence', 0)):.0%}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DarkGuard Compliance Report — {scan.url}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Inter',sans-serif; background:#fff; color:#1a1a2e; padding:40px; line-height:1.6; }}
  .header {{ display:flex; align-items:center; gap:24px; margin-bottom:32px; padding-bottom:24px; border-bottom:2px solid #eee; }}
  .grade-circle {{ width:72px; height:72px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:2rem; font-weight:800; color:white; background:{_grade_color(grade)}; }}
  .header-info h1 {{ font-size:1.5rem; font-weight:700; }}
  .header-info p {{ color:#666; font-size:0.85rem; }}
  .stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:32px; }}
  .stat {{ background:#f8f8fc; padding:16px; border-radius:8px; text-align:center; }}
  .stat-val {{ font-size:1.5rem; font-weight:800; color:#6c5ce7; }}
  .stat-label {{ font-size:0.7rem; color:#888; text-transform:uppercase; letter-spacing:0.06em; margin-top:4px; }}
  h2 {{ font-size:1.1rem; font-weight:700; margin:24px 0 12px; color:#333; }}
  table {{ width:100%; border-collapse:collapse; margin-bottom:24px; }}
  th {{ text-align:left; padding:10px 12px; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.06em; color:#888; background:#f8f8fc; border-bottom:1px solid #eee; }}
  td {{ padding:10px 12px; font-size:0.8rem; border-bottom:1px solid #f0f0f0; vertical-align:top; }}
  .sev {{ display:inline-block; padding:2px 8px; border-radius:12px; font-size:0.65rem; font-weight:700; }}
  .reg {{ display:inline-block; padding:2px 6px; border-radius:3px; font-size:0.6rem; font-weight:600; background:#6c5ce715; color:#6c5ce7; margin:1px; }}
  .footer {{ margin-top:40px; padding-top:16px; border-top:1px solid #eee; text-align:center; color:#aaa; font-size:0.7rem; }}
  @media print {{ body {{ padding:20px; }} .header {{ break-inside:avoid; }} table {{ break-inside:auto; }} tr {{ break-inside:avoid; }} }}
</style>
</head>
<body>
<div class="header">
  <div class="grade-circle">{grade}</div>
  <div class="header-info">
    <h1>Dark Pattern Compliance Report</h1>
    <p>{scan.url}</p>
    <p>Scanned: {scan.scanned_at.strftime('%B %d, %Y at %H:%M UTC')}</p>
  </div>
</div>

<div class="stats">
  <div class="stat"><div class="stat-val">{score.get('total', 0):.1f}</div><div class="stat-label">Dark Pattern Score</div></div>
  <div class="stat"><div class="stat-val">{score.get('pattern_count', 0)}</div><div class="stat-label">Patterns Found</div></div>
  <div class="stat"><div class="stat-val">{score.get('unique_categories', 0)}</div><div class="stat-label">Categories</div></div>
  <div class="stat"><div class="stat-val">{score.get('corroborated_count', 0)}</div><div class="stat-label">Corroborated</div></div>
</div>

<h2>Category Summary</h2>
<table><thead><tr><th>Category</th><th>Count</th><th>Severity</th><th>Max Confidence</th></tr></thead><tbody>{cat_rows}</tbody></table>

<h2>Regulations Potentially Violated ({len(regs)})</h2>
<table><thead><tr><th>Code</th><th>Regulation</th><th>Jurisdiction</th><th>Description</th></tr></thead><tbody>{reg_rows}</tbody></table>

<h2>Individual Detections ({detections.count()})</h2>
<table><thead><tr><th>Category</th><th>Severity</th><th>Confidence</th><th>Explanation</th><th>Analyzer</th><th>Regulations</th></tr></thead><tbody>{det_rows}</tbody></table>

<div class="footer">Generated by DarkGuard Auditing Platform · darkguard.dev</div>
</body>
</html>"""

    response = HttpResponse(html, content_type="text/html")
    response["Content-Disposition"] = f'inline; filename="darkguard-report-{scan_id}.html"'
    return response
