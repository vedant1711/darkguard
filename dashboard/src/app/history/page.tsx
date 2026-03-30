"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchScans, type ScanSummary } from "@/lib/api";

export default function HistoryPage() {
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [urlFilter, setUrlFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const loadScans = (filter: string, off: number) => {
    setLoading(true);
    fetchScans(filter || undefined, limit, off)
      .then((data) => {
        setScans(data.results);
        setTotal(data.total);
      })
      .catch(() => setScans([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadScans(urlFilter, offset);
  }, [urlFilter, offset]);

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="fade-in">
      <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: 8 }}>
        Scan History
      </h1>
      <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", marginBottom: 24 }}>
        {total} scans recorded
      </p>

      <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
        <input
          type="text"
          className="input"
          placeholder="Filter by URL…"
          value={urlFilter}
          onChange={(e) => {
            setUrlFilter(e.target.value);
            setOffset(0);
          }}
          style={{ maxWidth: 400 }}
        />
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Grade</th>
              <th>URL</th>
              <th>Score</th>
              <th>Patterns</th>
              <th>Categories</th>
              <th>Corroborated</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: 32 }}>
                  <div className="loading-spinner" style={{ display: "inline-block" }} />
                </td>
              </tr>
            ) : scans.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: 32, color: "var(--text-muted)" }}>
                  No scans found
                </td>
              </tr>
            ) : (
              scans.map((scan) => (
                <tr key={scan.id}>
                  <td>
                    <span className={`grade-badge grade-${scan.score_grade}`}>
                      {scan.score_grade}
                    </span>
                  </td>
                  <td>
                    <Link
                      href={`/scan/${scan.id}`}
                      style={{
                        color: "var(--accent)",
                        maxWidth: 280,
                        display: "inline-block",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {scan.url}
                    </Link>
                  </td>
                  <td>{scan.score_total.toFixed(1)}</td>
                  <td>{scan.pattern_count}</td>
                  <td>{scan.unique_categories}</td>
                  <td>{scan.corroborated_count}</td>
                  <td style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>
                    {new Date(scan.scanned_at).toLocaleDateString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "center", alignItems: "center" }}>
          <button
            className="btn btn-ghost"
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
          >
            ← Prev
          </button>
          <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            Page {currentPage} of {totalPages}
          </span>
          <button
            className="btn btn-ghost"
            onClick={() => setOffset(offset + limit)}
            disabled={currentPage >= totalPages}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
