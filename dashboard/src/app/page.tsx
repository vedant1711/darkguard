"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchScans, type ScanSummary } from "@/lib/api";
import styles from "./page.module.css";

export default function DashboardPage() {
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchScans(undefined, 10)
      .then((data) => setScans(data.results))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const totalScans = scans.length;
  const avgScore =
    totalScans > 0
      ? (scans.reduce((s, r) => s + r.score_total, 0) / totalScans).toFixed(1)
      : "—";
  const totalPatterns = scans.reduce((s, r) => s + r.pattern_count, 0);
  const worstGrade = scans.reduce((worst, r) => {
    const order = "ABCDF";
    return order.indexOf(r.score_grade) > order.indexOf(worst)
      ? r.score_grade
      : worst;
  }, "A");

  return (
    <div className="fade-in">
      <h1 className="pageTitle" style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: 8 }}>
        Dashboard
      </h1>
      <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", marginBottom: 32 }}>
        Overview of recent dark pattern audits
      </p>

      <div className={styles.statsGrid}>
        <div className={`card ${styles.statCard}`}>
          <div className={styles.statLabel}>Total Scans</div>
          <div className={`${styles.statValue} ${styles.statAccent}`}>
            {loading ? "…" : totalScans}
          </div>
        </div>
        <div className={`card ${styles.statCard}`}>
          <div className={styles.statLabel}>Avg Score</div>
          <div className={styles.statValue}>{loading ? "…" : avgScore}</div>
        </div>
        <div className={`card ${styles.statCard}`}>
          <div className={styles.statLabel}>Patterns Found</div>
          <div className={styles.statValue}>{loading ? "…" : totalPatterns}</div>
        </div>
        <div className={`card ${styles.statCard}`}>
          <div className={styles.statLabel}>Worst Grade</div>
          <div className={styles.statValue}>
            {loading ? "…" : (
              <span className={`grade-badge grade-${worstGrade}`}>{worstGrade}</span>
            )}
          </div>
        </div>
      </div>

      <h2 className={styles.recentTitle}>Recent Scans</h2>

      {error && <p style={{ color: "var(--severity-high)" }}>{error}</p>}

      {!loading && scans.length === 0 && !error ? (
        <div className={`card ${styles.empty}`}>
          <div className={styles.emptyIcon}>🛡️</div>
          <p className={styles.emptyText}>
            No scans yet. Start by auditing a URL.
          </p>
          <Link href="/scan" className="btn btn-primary">
            🔍 New Scan
          </Link>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Grade</th>
                <th>URL</th>
                <th>Score</th>
                <th>Patterns</th>
                <th>Categories</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 3 }).map((_, i) => (
                    <tr key={i}>
                      <td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)" }}>
                        <div className="loading-spinner" style={{ display: "inline-block" }} />
                      </td>
                    </tr>
                  ))
                : scans.map((scan) => (
                    <tr key={scan.id} className={styles.scanRow}>
                      <td>
                        <span className={`grade-badge grade-${scan.score_grade}`}>
                          {scan.score_grade}
                        </span>
                      </td>
                      <td>
                        <Link href={`/scan/${scan.id}`} className={styles.scanUrl}>
                          {scan.url}
                        </Link>
                      </td>
                      <td>{scan.score_total.toFixed(1)}</td>
                      <td>{scan.pattern_count}</td>
                      <td>{scan.unique_categories}</td>
                      <td style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                        {new Date(scan.scanned_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
