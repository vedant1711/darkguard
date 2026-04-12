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

// ── Deep Scan Types ──────────────────────────────────────

export interface DeepScanStep {
  step_number: number;
  page_url: string;
  page_title: string;
  action_taken: string;
  screenshot_b64: string;
  annotated_screenshot_b64: string;
  detections: DetectionItem[];
  patterns_found: number;
  timestamp: string;
  success: boolean;
  error: string;
}

export interface DeepScanWorkflow {
  workflow_id: string;
  workflow_name: string;
  workflow_description: string;
  workflow_icon: string;
  steps: DeepScanStep[];
  total_patterns: number;
  categories_found: string[];
  completed: boolean;
}

export interface DeepScanResult {
  url: string;
  workflows: DeepScanWorkflow[];
  summary: {
    total_patterns: number;
    total_steps: number;
    workflows_completed: number;
    workflows_total: number;
    categories_found: string[];
  };
  scan_id: number | null;
}

export interface WorkflowInfo {
  name: string;
  description: string;
  icon: string;
  step_count: number;
}

export async function fetchDeepScanWorkflows(): Promise<Record<string, WorkflowInfo>> {
  const res = await fetch(`${API_BASE}/scans/deep-scan/workflows`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const data = await res.json();
  return data.workflows;
}

export async function submitDeepScan(
  url: string,
  workflows?: string[]
): Promise<DeepScanResult> {
  const body: Record<string, unknown> = { url };
  if (workflows && workflows.length > 0) {
    body.workflows = workflows;
  }
  const res = await fetch(`${API_BASE}/scans/deep-scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Deep scan failed (${res.status}): ${text.slice(0, 200)}`);
  }
  return res.json();
}
