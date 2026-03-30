"use client";

import { useState } from "react";
import Link from "next/link";
import { submitScan, type AnalyzeResponse } from "@/lib/api";
import styles from "./scan.module.css";

export default function NewScanPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState("");

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const data = await submitScan(url.trim());
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setLoading(false);
    }
  };

  const report = result?.audit_report;
  const score = report?.score;
  const gradeClass = score ? `grade${score.grade}` : "";

  return (
    <div className="fade-in">
      <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: 8 }}>
        New Scan
      </h1>
      <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", marginBottom: 32 }}>
        Enter a URL to audit for dark patterns
      </p>

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
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? (
              <>
                <div className="loading-spinner" /> Scanning…
              </>
            ) : (
              "🔍 Scan"
            )}
          </button>
        </div>
      </form>

      {error && <div className={styles.errorMsg}>{error}</div>}

      {loading && (
        <div className={styles.loadingState}>
          <div className={styles.bigSpinner} />
          <span>Analyzing {url}…</span>
          <span style={{ fontSize: "0.75rem" }}>
            Running 10 analyzers, enriching regulations, computing score…
          </span>
        </div>
      )}

      {result && score && (
        <div className={`${styles.resultWrap} fade-in`}>
          <div className={`card ${styles.scoreCard}`}>
            <div className={`${styles.scoreCircle} ${styles[gradeClass]}`}>
              {score.grade}
              <span className={styles.scoreLabel}>Score {score.total}</span>
            </div>
            <div className={styles.scoreMeta}>
              <h3>Audit Complete</h3>
              <div className={styles.scoreStats}>
                <div className={styles.scoreStatItem}>
                  <strong>{score.pattern_count}</strong> patterns
                </div>
                <div className={styles.scoreStatItem}>
                  <strong>{score.unique_categories}</strong> categories
                </div>
                <div className={styles.scoreStatItem}>
                  <strong>{score.corroborated_count}</strong> corroborated
                </div>
                <div className={styles.scoreStatItem}>
                  <strong>{score.severity_distribution?.high || 0}</strong> high severity
                </div>
              </div>
            </div>
          </div>

          {result.scan_id && (
            <div className={styles.viewReportBtn}>
              <Link href={`/scan/${result.scan_id}`} className="btn btn-ghost">
                📋 View Full Report
              </Link>
            </div>
          )}

          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, margin: "24px 0 16px" }}>
            Detections ({result.detections.length})
          </h2>

          <div className={styles.detectionsList}>
            {result.detections.length === 0 ? (
              <div className="card" style={{ textAlign: "center", padding: 32 }}>
                <p style={{ color: "var(--grade-a)", fontSize: "1.5rem", marginBottom: 8 }}>✨</p>
                <p style={{ color: "var(--text-secondary)" }}>No dark patterns detected!</p>
              </div>
            ) : (
              result.detections.map((det, i) => (
                <div key={i} className={`card ${styles.detectionCard}`}>
                  <div className={styles.detectionHeader}>
                    <span className={styles.detectionCategory}>
                      {det.category.replace(/_/g, " ")}
                    </span>
                    <span className={`severity-badge severity-${det.severity}`}>
                      {det.severity}
                    </span>
                    {det.corroborated && (
                      <span className={styles.corrobBadge}>✓ Corroborated</span>
                    )}
                  </div>
                  <p className={styles.detectionExplanation}>{det.explanation}</p>
                  <div className={styles.detectionMeta}>
                    <span className={styles.analyzerBadge}>
                      {det.analyzer_name || "unknown"}
                    </span>
                    <span className={styles.confidence}>
                      {(det.confidence * 100).toFixed(0)}% confidence
                    </span>
                    {det.regulation_refs.map((ref) => (
                      <span key={ref} className="reg-badge">
                        {ref}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
