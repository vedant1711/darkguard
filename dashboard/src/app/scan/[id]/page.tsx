"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchScanDetail, fetchScanReport, type ScanDetail, type AuditReport } from "@/lib/api";
import styles from "../scan.module.css";

export default function ScanDetailPage() {
  const params = useParams();
  const scanId = Number(params.id);
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [report, setReport] = useState<AuditReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!scanId) return;
    Promise.all([fetchScanDetail(scanId), fetchScanReport(scanId)])
      .then(([detail, rpt]) => {
        setScan(detail);
        setReport(rpt);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [scanId]);

  if (loading) {
    return (
      <div className={styles.loadingState}>
        <div className={styles.bigSpinner} />
        <span>Loading scan #{scanId}…</span>
      </div>
    );
  }

  if (error || !scan) {
    return (
      <div className="fade-in">
        <div className={styles.errorMsg}>{error || "Scan not found"}</div>
        <Link href="/history" className="btn btn-ghost" style={{ marginTop: 16 }}>
          ← Back to History
        </Link>
      </div>
    );
  }

  const gradeClass = `grade${scan.score_grade}`;

  return (
    <div className="fade-in">
      <Link href="/history" style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
        ← Back to History
      </Link>

      <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", margin: "16px 0 4px" }}>
        Scan #{scan.id}
      </h1>
      <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginBottom: 28, wordBreak: "break-all" }}>
        {scan.url} · {new Date(scan.scanned_at).toLocaleString()}
      </p>

      {/* Score Card */}
      <div className={`card ${styles.scoreCard}`}>
        <div className={`${styles.scoreCircle} ${styles[gradeClass]}`}>
          {scan.score_grade}
          <span className={styles.scoreLabel}>{scan.score_total.toFixed(1)}</span>
        </div>
        <div className={styles.scoreMeta}>
          <h3>Audit Score</h3>
          <div className={styles.scoreStats}>
            <div className={styles.scoreStatItem}>
              <strong>{scan.pattern_count}</strong> patterns
            </div>
            <div className={styles.scoreStatItem}>
              <strong>{scan.unique_categories}</strong> categories
            </div>
            <div className={styles.scoreStatItem}>
              <strong>{scan.corroborated_count}</strong> corroborated
            </div>
          </div>
        </div>
      </div>

      {/* Regulation Violations */}
      {report && report.regulations_violated.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: 12 }}>
            Regulations Violated ({report.regulations_violated.length})
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {report.regulations_violated.map((reg) => (
              <div key={reg.code} className="card" style={{ padding: "14px 18px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                  <span className="reg-badge">{reg.code}</span>
                  <strong style={{ fontSize: "0.85rem" }}>{reg.name}</strong>
                  <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                    {reg.jurisdiction}
                  </span>
                </div>
                <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  {reg.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Category Summary */}
      {report && Object.keys(report.category_summary).length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: 12 }}>
            Category Summary
          </h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Count</th>
                  <th>Max Confidence</th>
                  <th>Severity</th>
                  <th>Regulations</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(report.category_summary).map(([cat, data]) => (
                  <tr key={cat}>
                    <td style={{ fontWeight: 600 }}>{cat.replace(/_/g, " ")}</td>
                    <td>{data.count}</td>
                    <td>{(data.max_confidence * 100).toFixed(0)}%</td>
                    <td>
                      <span className={`severity-badge severity-${data.severity}`}>
                        {data.severity}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        {data.regulations.map((r: string) => (
                          <span key={r} className="reg-badge">{r}</span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Individual Detections */}
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: 12 }}>
        Detections ({scan.detections.length})
      </h2>
      <div className={styles.detectionsList}>
        {scan.detections.map((det, i) => (
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
              <span className={styles.analyzerBadge}>{det.analyzer_name}</span>
              <span className={styles.confidence}>
                {(det.confidence * 100).toFixed(0)}% confidence
              </span>
              {det.regulation_refs.map((ref) => (
                <span key={ref} className="reg-badge">{ref}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
