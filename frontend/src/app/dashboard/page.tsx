"use client";

import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface StatsOverview {
  current_elo: number | null;
  winrate: number | null;
  total_games: number;
  avg_accuracy: number | null;
}

interface EloPoint {
  date: string;
  elo: number;
}

interface OpeningStat {
  name: string;
  total_games: number;
  wins: number;
  draws: number;
  losses: number;
  winrate: number;
}

interface DashboardData {
  overview: StatsOverview | null;
  eloHistory: EloPoint[];
  openings: OpeningStat[];
}

const kpiTileStyle: React.CSSProperties = {
  flex: 1,
  minWidth: 0,
  background: "var(--bg-secondary)",
  border: "1px solid var(--border)",
  padding: "24px",
};

const sectionStyle: React.CSSProperties = {
  marginBottom: "32px",
};

const sectionHeaderStyle: React.CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  textTransform: "uppercase" as const,
  letterSpacing: "0.08em",
  color: "var(--fg-secondary)",
  marginBottom: "16px",
  borderBottom: "1px solid var(--border)",
  paddingBottom: "8px",
};

const kpiValueStyle: React.CSSProperties = {
  fontSize: "32px",
  fontWeight: 700,
  lineHeight: 1,
  marginBottom: "6px",
};

const kpiLabelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "var(--fg-secondary)",
  textTransform: "uppercase" as const,
  letterSpacing: "0.06em",
};

function formatPct(val: number | null): string {
  if (val === null || val === undefined) return "-";
  return `${Math.round(val * 100)}%`;
}

function formatNum(val: number | null): string {
  if (val === null || val === undefined) return "-";
  return val.toLocaleString("nl-NL");
}

function WinrateBar({ wins, draws, losses, total }: { wins: number; draws: number; losses: number; total: number }) {
  if (total === 0) return <div style={{ height: 8, background: "var(--border)" }} />;
  const wPct = (wins / total) * 100;
  const dPct = (draws / total) * 100;
  const lPct = (losses / total) * 100;
  return (
    <div style={{ display: "flex", height: 8, width: "100%" }}>
      <div style={{ width: `${wPct}%`, background: "var(--success)" }} />
      <div style={{ width: `${dPct}%`, background: "var(--fg-secondary)" }} />
      <div style={{ width: `${lPct}%`, background: "var(--danger)" }} />
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData>({
    overview: null,
    eloHistory: [],
    openings: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const opts: RequestInit = { credentials: "include" };

    Promise.all([
      fetch(`${API_URL}/api/stats/overview`, opts),
      fetch(`${API_URL}/api/stats/openings`, opts),
      fetch(`${API_URL}/api/stats/elo-history`, opts),
    ])
      .then(async ([overviewRes, openingsRes, eloRes]) => {
        const overview = overviewRes.ok ? await overviewRes.json() : null;
        const openings = openingsRes.ok ? await openingsRes.json() : [];
        const eloHistory = eloRes.ok ? await eloRes.json() : [];
        setData({ overview, openings, eloHistory });
      })
      .catch(() => setError("Kon statistieken niet laden."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <main style={{ padding: "32px", display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh" }}>
        <p style={{ color: "var(--fg-secondary)" }}>Statistieken laden...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main style={{ padding: "32px" }}>
        <p style={{ color: "var(--danger)" }}>{error}</p>
      </main>
    );
  }

  const { overview, eloHistory, openings } = data;

  return (
    <main style={{ padding: "32px", maxWidth: "1200px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "24px", fontWeight: 600, marginBottom: "32px" }}>Dashboard</h1>

      {/* KPI Tiles */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>Samenvatting</div>
        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" as const }}>
          <div style={kpiTileStyle}>
            <div style={kpiValueStyle}>{overview?.current_elo != null ? formatNum(overview.current_elo) : "-"}</div>
            <div style={kpiLabelStyle}>Huidige Elo</div>
          </div>
          <div style={kpiTileStyle}>
            <div style={kpiValueStyle}>{formatPct(overview?.winrate ?? null)}</div>
            <div style={kpiLabelStyle}>Winrate</div>
          </div>
          <div style={kpiTileStyle}>
            <div style={kpiValueStyle}>{formatNum(overview?.total_games ?? null)}</div>
            <div style={kpiLabelStyle}>Totaal partijen</div>
          </div>
          <div style={kpiTileStyle}>
            <div style={kpiValueStyle}>{formatPct(overview?.avg_accuracy ?? null)}</div>
            <div style={kpiLabelStyle}>Gem. nauwkeurigheid</div>
          </div>
        </div>
      </div>

      {/* Elo History Chart */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>Elo verloop</div>
        {eloHistory.length === 0 ? (
          <div
            style={{
              border: "1px solid var(--border)",
              background: "var(--bg-secondary)",
              padding: "48px",
              textAlign: "center",
              color: "var(--fg-secondary)",
              fontSize: "14px",
            }}
          >
            Geen Elo-geschiedenis beschikbaar
          </div>
        ) : (
          <div style={{ border: "1px solid var(--border)", background: "var(--bg-secondary)", padding: "24px 8px 8px 8px" }}>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={eloHistory} margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
                <XAxis
                  dataKey="date"
                  tick={{ fill: "var(--fg-secondary)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: "var(--border)" }}
                  minTickGap={60}
                />
                <YAxis
                  tick={{ fill: "var(--fg-secondary)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  width={48}
                  domain={["auto", "auto"]}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--bg)",
                    border: "1px solid var(--border)",
                    borderRadius: 0,
                    color: "var(--fg)",
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "var(--fg-secondary)" }}
                  cursor={{ stroke: "var(--border)" }}
                />
                <Line
                  type="monotone"
                  dataKey="elo"
                  stroke="var(--fg)"
                  strokeWidth={1.5}
                  dot={false}
                  activeDot={{ r: 3, fill: "var(--fg)" }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Opening Stats */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>Openingen</div>
        {openings.length === 0 ? (
          <div
            style={{
              border: "1px solid var(--border)",
              background: "var(--bg-secondary)",
              padding: "48px",
              textAlign: "center",
              color: "var(--fg-secondary)",
              fontSize: "14px",
            }}
          >
            Geen openingsstatistieken beschikbaar
          </div>
        ) : (
          <div style={{ border: "1px solid var(--border)" }}>
            {/* Table header */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 80px 200px 120px",
                gap: "16px",
                padding: "10px 16px",
                background: "var(--bg-secondary)",
                borderBottom: "1px solid var(--border)",
                fontSize: "11px",
                fontWeight: 600,
                textTransform: "uppercase" as const,
                letterSpacing: "0.06em",
                color: "var(--fg-secondary)",
              }}
            >
              <span>Opening</span>
              <span style={{ textAlign: "right" }}>Partijen</span>
              <span>Resultaten</span>
              <span style={{ textAlign: "right" }}>Winrate</span>
            </div>
            {openings.map((op, i) => (
              <div
                key={op.name}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 80px 200px 120px",
                  gap: "16px",
                  padding: "12px 16px",
                  borderBottom: i < openings.length - 1 ? "1px solid var(--border)" : "none",
                  alignItems: "center",
                }}
              >
                <span style={{ fontSize: "14px", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" as const }}>
                  {op.name}
                </span>
                <span style={{ fontSize: "14px", textAlign: "right", color: "var(--fg-secondary)" }}>
                  {op.total_games}
                </span>
                <div>
                  <WinrateBar wins={op.wins} draws={op.draws} losses={op.losses} total={op.total_games} />
                  <div style={{ display: "flex", gap: "8px", marginTop: "4px", fontSize: "11px", color: "var(--fg-secondary)" }}>
                    <span style={{ color: "var(--success)" }}>{op.wins}W</span>
                    <span>{op.draws}R</span>
                    <span style={{ color: "var(--danger)" }}>{op.losses}V</span>
                  </div>
                </div>
                <span style={{ fontSize: "14px", fontWeight: 600, textAlign: "right" }}>
                  {Math.round(op.winrate * 100)}%
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
