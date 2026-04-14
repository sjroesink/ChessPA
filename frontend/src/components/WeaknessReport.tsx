"use client";
import { useEffect, useState } from "react";
import { apiJson } from "@/lib/api";
import MotifBadge from "./MotifBadge";

interface Data {
  games_analyzed: number;
  per_opening: { eco: string; name: string; games: number; avg_accuracy: number }[];
  per_phase: Record<string, number>;
  top_motifs: { type: string; count: number }[];
}

const PHASE_LABEL: Record<string, string> = {
  opening: "Opening",
  middlegame: "Middenspel",
  endgame: "Eindspel",
};

export default function WeaknessReport() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiJson<Data>("/api/coaching/weaknesses")
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <p style={{ color: "#b91c1c" }}>{error}</p>;
  if (!data) return <p>Laden…</p>;
  if (data.games_analyzed === 0) return <p>Nog geen geanalyseerde partijen.</p>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <p style={{ fontSize: 13, color: "var(--muted, #666)" }}>
        {data.games_analyzed} partijen geanalyseerd.
      </p>

      <section>
        <h3 style={{ fontSize: 14, margin: "0 0 6px" }}>Zwakste openingen</h3>
        {data.per_opening.length === 0 ? (
          <p style={{ fontSize: 13 }}>Geen openingsdata beschikbaar.</p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {data.per_opening.slice(0, 5).map((o) => (
              <li
                key={o.eco}
                style={{
                  display: "flex",
                  gap: 8,
                  padding: "4px 0",
                  borderBottom: "1px solid var(--border)",
                  fontSize: 13,
                }}
              >
                <span style={{ fontFamily: "monospace", width: 48 }}>{o.eco}</span>
                <span style={{ flex: 1 }}>{o.name}</span>
                <span style={{ color: "var(--muted, #888)" }}>{o.games}×</span>
                <span style={{ width: 56, textAlign: "right" }}>
                  {o.avg_accuracy.toFixed(0)}%
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h3 style={{ fontSize: 14, margin: "0 0 6px" }}>Gemiste motieven</h3>
        {data.top_motifs.length === 0 ? (
          <p style={{ fontSize: 13 }}>Geen motieven gedetecteerd (nog).</p>
        ) : (
          <div>
            {data.top_motifs.map((m) => (
              <span key={m.type} style={{ marginRight: 6 }}>
                <MotifBadge motif={{ type: m.type }} />
                <span style={{ fontSize: 12, color: "var(--muted, #666)" }}>×{m.count}</span>
              </span>
            ))}
          </div>
        )}
      </section>

      <section>
        <h3 style={{ fontSize: 14, margin: "0 0 6px" }}>ACPL per fase</h3>
        {Object.keys(data.per_phase).length === 0 ? (
          <p style={{ fontSize: 13 }}>Geen fase-data.</p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, fontSize: 13 }}>
            {Object.entries(data.per_phase).map(([p, v]) => (
              <li key={p} style={{ display: "flex", gap: 8 }}>
                <span style={{ width: 120 }}>{PHASE_LABEL[p] ?? p}</span>
                <span>{v.toFixed(0)} cpl</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
