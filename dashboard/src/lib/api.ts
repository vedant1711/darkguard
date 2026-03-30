const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export interface ScanSummary {
  id: number;
  url: string;
  scanned_at: string;
  score_total: number;
  score_grade: string;
  pattern_count: number;
  unique_categories: number;
  corroborated_count: number;
}

export interface ScanListResponse {
  total: number;
  limit: number;
  offset: number;
  results: ScanSummary[];
}

export interface DetectionItem {
  id: number;
  category: string;
  element_selector: string;
  confidence: number;
  explanation: string;
  severity: string;
  corroborated: boolean;
  analyzer_name: string;
  platform_context: string;
  regulation_refs: string[];
}

export interface ScanDetail extends ScanSummary {
  detections: DetectionItem[];
}

export interface AuditReport {
  metadata: { url: string; timestamp: string; analyzer_version: string };
  score: {
    total: number;
    grade: string;
    pattern_count: number;
    unique_categories: number;
    corroborated_count: number;
    severity_distribution: Record<string, number>;
  };
  category_summary: Record<
    string,
    { count: number; max_confidence: number; severity: string; regulations: string[] }
  >;
  regulations_violated: {
    code: string;
    name: string;
    jurisdiction: string;
    description: string;
  }[];
  detections: DetectionItem[];
}

export interface BenchmarkResult {
  site_score: number;
  industry_avg: number;
  percentile_rank: string;
  delta: number;
  platform_context: string;
  categories_above_average: string[];
  categories_below_average: string[];
}

export interface AnalyzeResponse {
  detections: DetectionItem[];
  audit_report: AuditReport;
  scan_id: number | null;
  benchmark?: BenchmarkResult;
}

export async function fetchScans(
  url?: string,
  limit = 20,
  offset = 0
): Promise<ScanListResponse> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (url) params.set("url", url);
  const res = await fetch(`${API_BASE}/scans/?${params}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchScanDetail(id: number): Promise<ScanDetail> {
  const res = await fetch(`${API_BASE}/scans/${id}/`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchScanReport(id: number): Promise<AuditReport> {
  const res = await fetch(`${API_BASE}/scans/${id}/report/`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export function getPdfReportUrl(scanId: number): string {
  return `${API_BASE}/scans/${scanId}/report/pdf`;
}

export async function submitScan(url: string): Promise<AnalyzeResponse> {
  // Use the server-side Playwright crawler for real page analysis
  const res = await fetch(`${API_BASE}/scans/crawl`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Analysis failed (${res.status}): ${text.slice(0, 200)}`);
  }
  return res.json();
}

