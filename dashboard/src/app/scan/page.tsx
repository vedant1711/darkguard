"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { submitScan, submitDeepScan, fetchDeepScanWorkflows, type AnalyzeResponse, type DeepScanResult, type WorkflowInfo } from "@/lib/api";
import styles from "./scan.module.css";

type ScanMode = "quick" | "deep";

export default function NewScanPage() {
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState<ScanMode>("quick");
  const [loading, setLoading] = useState(false);
  const [quickResult, setQuickResult] = useState<AnalyzeResponse | null>(null);
  const [deepResult, setDeepResult] = useState<DeepScanResult | null>(null);
  const [error, setError] = useState("");
  const [workflows, setWorkflows] = useState<Record<string, WorkflowInfo>>({});
  const [selectedWorkflows, setSelectedWorkflows] = useState<string[]>([]);
  const [expandedWorkflow, setExpandedWorkflow] = useState<string | null>(null);

  useEffect(() => {
    fetchDeepScanWorkflows()
      .then((wf) => {
        setWorkflows(wf);
        setSelectedWorkflows(Object.keys(wf));
      })
      .catch(() => {});
  }, []);

  const toggleWorkflow = (id: string) => {
    setSelectedWorkflows((prev) =>
      prev.includes(id) ? prev.filter((w) => w !== id) : [...prev, id]
    );
  };

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError("");
    setQuickResult(null);
    setDeepResult(null);

    try {
      if (mode === "quick") {
        const data = await submitScan(url.trim());
        setQuickResult(data);
      } else {
        const data = await submitDeepScan(url.trim(), selectedWorkflows);
        setDeepResult(data);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setLoading(false);
    }
  };

  const report = quickResult?.audit_report;
  const score = report?.score;
  const gradeClass = score ? `grade${score.grade}` : "";

  return (
    <div className="fade-in">
      <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: 8 }}>
        New Scan
      </h1>
      <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", marginBottom: 24 }}>
        Enter a URL to audit for dark patterns
      </p>

      {/* Scan mode toggle */}
      <div className={styles.modeToggle}>
        <button
          className={`${styles.modeBtn} ${mode === "quick" ? styles.modeBtnActive : ""}`}
          onClick={() => setMode("quick")}
          type="button"
        >
          ⚡ Quick Scan
        </button>
        <button
          className={`${styles.modeBtn} ${mode === "deep" ? styles.modeBtnActive : ""}`}
          onClick={() => setMode("deep")}
          type="button"
        >
          🔬 Deep Scan
        </button>
      </div>

      {mode === "deep" && (
        <p className={styles.modeDescription}>
          Deep Scan navigates through real workflows (search, checkout, settings) and takes annotated screenshots at each step to find dark patterns across the entire user journey.
        </p>
      )}

      <form onSubmit={handleScan} className={styles.scanForm}>
        <div className={styles.inputGroup}>
          <input
            type="url"
            className="input"
            placeholder="https://example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
            disabled={loading}
          />
          <button type="submit" className="btn btn-primary" disabled={loading || (mode === "deep" && selectedWorkflows.length === 0)}>
            {loading ? (
              <>
                <div className="loading-spinner" /> {mode === "deep" ? "Deep Scanning…" : "Scanning…"}
              </>
            ) : (
              mode === "deep" ? "🔬 Deep Scan" : "🔍 Scan"
            )}
          </button>
        </div>
      </form>

      {/* Workflow picker (Deep Scan mode) */}
      {mode === "deep" && !loading && !deepResult && (
        <div className={styles.workflowPicker}>
          <h3 style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: 12 }}>
            Select Workflows
          </h3>
          <div className={styles.workflowGrid}>
            {Object.entries(workflows).map(([id, wf]) => (
              <button
                key={id}
                type="button"
                className={`${styles.workflowCard} ${selectedWorkflows.includes(id) ? styles.workflowCardSelected : ""}`}
                onClick={() => toggleWorkflow(id)}
              >
                <span className={styles.workflowIcon}>{wf.icon}</span>
                <span className={styles.workflowName}>{wf.name}</span>
                <span className={styles.workflowDesc}>{wf.description}</span>
                <span className={styles.workflowSteps}>{wf.step_count} steps</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {error && <div className={styles.errorMsg}>{error}</div>}

      {loading && (
        <div className={styles.loadingState}>
          <div className={styles.bigSpinner} />
          <span>{mode === "deep" ? `Deep scanning ${url}…` : `Analyzing ${url}…`}</span>
          <span style={{ fontSize: "0.75rem" }}>
            {mode === "deep"
              ? `Navigating ${selectedWorkflows.length} workflow(s), analyzing each page…`
              : "Running 10 analyzers, enriching regulations, computing score…"}
          </span>
        </div>
      )}

      {/* ── Quick Scan Results ── */}
      {quickResult && score && (
        <div className={`${styles.resultWrap} fade-in`}>
          <div className={`card ${styles.scoreCard}`}>
            <div className={`${styles.scoreCircle} ${styles[gradeClass]}`}>
              {score.grade}
              <span className={styles.scoreLabel}>Score {score.total}</span>
            </div>
            <div className={styles.scoreMeta}>
              <h3>Audit Complete</h3>
              <div className={styles.scoreStats}>
                <div className={styles.scoreStatItem}><strong>{score.pattern_count}</strong> patterns</div>
                <div className={styles.scoreStatItem}><strong>{score.unique_categories}</strong> categories</div>
                <div className={styles.scoreStatItem}><strong>{score.corroborated_count}</strong> corroborated</div>
                <div className={styles.scoreStatItem}><strong>{score.severity_distribution?.high || 0}</strong> high severity</div>
              </div>
            </div>
          </div>

          {quickResult.scan_id && (
            <div className={styles.viewReportBtn}>
              <Link href={`/scan/${quickResult.scan_id}`} className="btn btn-ghost">📋 View Full Report</Link>
            </div>
          )}

          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, margin: "24px 0 16px" }}>
            Detections ({quickResult.detections.length})
          </h2>

          <div className={styles.detectionsList}>
            {quickResult.detections.length === 0 ? (
              <div className="card" style={{ textAlign: "center", padding: 32 }}>
                <p style={{ color: "var(--grade-a)", fontSize: "1.5rem", marginBottom: 8 }}>✨</p>
                <p style={{ color: "var(--text-secondary)" }}>No dark patterns detected!</p>
              </div>
            ) : (
              quickResult.detections.map((det, i) => (
                <div key={i} className={`card ${styles.detectionCard}`}>
                  <div className={styles.detectionHeader}>
                    <span className={styles.detectionCategory}>{det.category.replace(/_/g, " ")}</span>
                    <span className={`severity-badge severity-${det.severity}`}>{det.severity}</span>
                    {det.corroborated && <span className={styles.corrobBadge}>✓ Corroborated</span>}
                  </div>
                  <p className={styles.detectionExplanation}>{det.explanation}</p>
                  <div className={styles.detectionMeta}>
                    <span className={styles.analyzerBadge}>{det.analyzer_name || "unknown"}</span>
                    <span className={styles.confidence}>{(det.confidence * 100).toFixed(0)}% confidence</span>
                    {det.regulation_refs.map((ref) => (
                      <span key={ref} className="reg-badge">{ref}</span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ── Deep Scan Results ── */}
      {deepResult && (
        <div className={`${styles.resultWrap} fade-in`}>
          {/* Summary */}
          <div className={`card ${styles.deepSummary}`}>
            <div className={styles.deepSummaryIcon}>🔬</div>
            <div className={styles.deepSummaryContent}>
              <h3>Deep Scan Complete</h3>
              <div className={styles.scoreStats}>
                <div className={styles.scoreStatItem}><strong>{deepResult.summary.total_patterns}</strong> patterns found</div>
                <div className={styles.scoreStatItem}><strong>{deepResult.summary.total_steps}</strong> pages analyzed</div>
                <div className={styles.scoreStatItem}><strong>{deepResult.summary.workflows_completed}</strong> workflows</div>
                <div className={styles.scoreStatItem}><strong>{deepResult.summary.categories_found?.length || 0}</strong> categories</div>
              </div>
            </div>
          </div>

          {/* Workflow cards */}
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, margin: "24px 0 16px" }}>
            Workflow Results
          </h2>

          <div className={styles.workflowResults}>
            {deepResult.workflows.map((wf) => (
              <div key={wf.workflow_id} className={styles.workflowResultCard}>
                <button
                  className={styles.workflowResultHeader}
                  onClick={() => setExpandedWorkflow(expandedWorkflow === wf.workflow_id ? null : wf.workflow_id)}
                  type="button"
                >
                  <span className={styles.workflowIcon}>{wf.workflow_icon}</span>
                  <div className={styles.workflowResultMeta}>
                    <strong>{wf.workflow_name}</strong>
                    <span>{wf.steps.length} steps · {wf.total_patterns} patterns</span>
                  </div>
                  <div className={styles.workflowCategories}>
                    {wf.categories_found.slice(0, 3).map((cat) => (
                      <span key={cat} className="reg-badge">{cat.replace(/_/g, " ")}</span>
                    ))}
                    {wf.categories_found.length > 3 && (
                      <span className="reg-badge">+{wf.categories_found.length - 3}</span>
                    )}
                  </div>
                  <span className={styles.expandIcon}>{expandedWorkflow === wf.workflow_id ? "▼" : "▶"}</span>
                </button>

                {/* Expanded timeline */}
                {expandedWorkflow === wf.workflow_id && (
                  <div className={styles.timeline}>
                    {wf.steps.map((step, idx) => (
                      <div key={idx} className={styles.timelineStep}>
                        <div className={styles.timelineConnector}>
                          <div className={`${styles.timelineDot} ${step.patterns_found > 0 ? styles.timelineDotAlert : ""}`}>
                            {step.patterns_found > 0 ? "⚠" : "✓"}
                          </div>
                          {idx < wf.steps.length - 1 && <div className={styles.timelineLine} />}
                        </div>

                        <div className={styles.timelineContent}>
                          <div className={styles.stepHeader}>
                            <span className={styles.stepNumber}>Step {step.step_number}</span>
                            <span className={styles.stepAction}>{step.action_taken}</span>
                            {step.patterns_found > 0 && (
                              <span className="severity-badge severity-high">{step.patterns_found} patterns</span>
                            )}
                          </div>

                          <div className={styles.stepUrl}>{step.page_title || step.page_url}</div>

                          {/* Annotated screenshot */}
                          {step.annotated_screenshot_b64 && (
                            <div className={styles.screenshotWrap}>
                              <img
                                src={`data:image/png;base64,${step.annotated_screenshot_b64}`}
                                alt={`Step ${step.step_number} - ${step.action_taken}`}
                                className={styles.screenshot}
                              />
                            </div>
                          )}

                          {/* Detections for this step */}
                          {step.detections.length > 0 && (
                            <div className={styles.stepDetections}>
                              {step.detections.map((det, di) => (
                                <div key={di} className={`card ${styles.detectionCard}`}>
                                  <div className={styles.detectionHeader}>
                                    <span className={styles.detectionCategory}>{det.category.replace(/_/g, " ")}</span>
                                    <span className={`severity-badge severity-${det.severity}`}>{det.severity}</span>
                                  </div>
                                  <p className={styles.detectionExplanation}>{det.explanation}</p>
                                  <div className={styles.detectionMeta}>
                                    <span className={styles.analyzerBadge}>{det.analyzer_name}</span>
                                    <span className={styles.confidence}>{(det.confidence * 100).toFixed(0)}%</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
