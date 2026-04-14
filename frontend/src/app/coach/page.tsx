"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import WeaknessReport from "@/components/WeaknessReport";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ConnectedAccount {
  platform: string;
  username: string;
}

interface UserInfo {
  id: number;
  username: string;
  email: string;
  connected_accounts: ConnectedAccount[];
}

interface StatsOverview {
  current_elo: number | null;
  winrate: number | null;
  total_games: number;
  avg_accuracy: number | null;
}

interface Game {
  id: number;
  white_username: string;
  black_username: string;
  user_color: "white" | "black";
  result: string; // "win" | "loss" | "draw"
  opening_name: string;
  time_category: string;
  user_elo: number;
  played_at: string;
}

interface GamesResponse {
  games: Game[];
  total: number;
}

interface CoachingInsight {
  id: string;
  type: "weakness" | "pattern" | "strength";
  title: string;
  description: string;
  severity: string;
  related_games: string[];
  generated_at: string | null;
  model_version: string;
}

// ---- helpers ----

function formatNum(val: number | null | undefined): string {
  if (val === null || val === undefined) return "-";
  return String(val);
}

function formatPct(val: number | null | undefined): string {
  if (val === null || val === undefined) return "-";
  return `${Math.round(val)}%`;
}

function getOpponent(game: Game): string {
  return game.user_color === "white" ? game.black_username : game.white_username;
}

function getResultLabel(game: Game): { label: string; color: string } {
  if (game.result === "draw") return { label: "Remise", color: "var(--fg-secondary)" };
  if (game.result === "win") return { label: "Winst", color: "var(--success)" };
  return { label: "Verlies", color: "var(--danger)" };
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const months = ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"];
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
}

function insightBorderColor(type: CoachingInsight["type"]): string {
  if (type === "weakness") return "var(--danger)";
  if (type === "pattern") return "var(--warning)";
  return "var(--success)";
}

function insightTypeBadge(type: CoachingInsight["type"]): string {
  if (type === "weakness") return "Zwakte";
  if (type === "pattern") return "Patroon";
  return "Sterkte";
}

function insightBadgeColor(type: CoachingInsight["type"]): string {
  if (type === "weakness") return "var(--danger)";
  if (type === "pattern") return "var(--warning)";
  return "var(--success)";
}

function severityLabel(severity: string): string {
  const s = severity.toLowerCase();
  if (s === "high") return "Hoog";
  if (s === "medium") return "Gemiddeld";
  if (s === "low") return "Laag";
  return severity;
}

// ---- style constants ----

const sectionHeaderStyle: React.CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  color: "var(--fg-secondary)",
  marginBottom: "16px",
  borderBottom: "1px solid var(--border)",
  paddingBottom: "8px",
};

const sectionStyle: React.CSSProperties = {
  marginBottom: "32px",
};

const kpiTileStyle: React.CSSProperties = {
  flex: 1,
  minWidth: "120px",
  background: "var(--bg-secondary)",
  border: "1px solid var(--border)",
  padding: "20px 24px",
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
  textTransform: "uppercase",
  letterSpacing: "0.06em",
};

// ---- component ----

export default function CoachPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [overview, setOverview] = useState<StatsOverview | null>(null);
  const [recentGames, setRecentGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [insights, setInsights] = useState<CoachingInsight[]>([]);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [refreshLoading, setRefreshLoading] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);

  const fetchInsights = useCallback(async () => {
    setInsightsLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/coaching/insights`, {
        credentials: "include",
      });
      if (res.ok) {
        const data: CoachingInsight[] = await res.json();
        setInsights(data);
      }
    } catch {
      // silently ignore; insights section shows empty state
    } finally {
      setInsightsLoading(false);
    }
  }, []);

  useEffect(() => {
    const opts: RequestInit = { credentials: "include" };

    Promise.all([
      fetch(`${API_URL}/auth/me`, opts),
      fetch(`${API_URL}/api/stats/overview`, opts),
      fetch(`${API_URL}/api/games?limit=5`, opts),
    ])
      .then(async ([meRes, statsRes, gamesRes]) => {
        if (!meRes.ok) throw new Error("Niet ingelogd");
        const userData: UserInfo = await meRes.json();
        const statsData: StatsOverview | null = statsRes.ok ? await statsRes.json() : null;
        const gamesData: GamesResponse | null = gamesRes.ok ? await gamesRes.json() : null;
        setUser(userData);
        setOverview(statsData);
        setRecentGames(gamesData?.games ?? []);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));

    fetchInsights();
  }, [fetchInsights]);

  async function handleSync() {
    setSyncLoading(true);
    setSyncMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/games/sync`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setSyncMessage("Synchronisatie gestart. Partijen worden op de achtergrond geladen.");
    } catch {
      setSyncMessage("Synchronisatie mislukt. Probeer het opnieuw.");
    } finally {
      setSyncLoading(false);
    }
  }

  async function handleRefreshInsights() {
    setRefreshLoading(true);
    setRefreshMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/coaching/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setRefreshMessage("Inzichten worden gegenereerd...");
      await fetchInsights();
      setRefreshMessage(null);
    } catch {
      setRefreshMessage("Vernieuwen mislukt. Probeer het opnieuw.");
    } finally {
      setRefreshLoading(false);
    }
  }

  if (loading) {
    return (
      <main style={{ padding: "32px", display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh" }}>
        <p style={{ color: "var(--fg-secondary)" }}>Laden...</p>
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

  const connectedAccounts = user?.connected_accounts ?? [];

  return (
    <main style={{ padding: "32px", maxWidth: "1100px", margin: "0 auto" }}>
      {/* Welcome header */}
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: 700, marginBottom: "4px" }}>
          Welkom, {user?.username ?? "Speler"}
        </h1>
        <p style={{ color: "var(--fg-secondary)", fontSize: "14px" }}>
          Jouw persoonlijk schaakcoach dashboard
        </p>
      </div>

      {/* Quick stats row */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>Snelle statistieken</div>
        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
          <div style={kpiTileStyle}>
            <div style={kpiValueStyle}>
              {overview?.current_elo != null ? formatNum(overview.current_elo) : "-"}
            </div>
            <div style={kpiLabelStyle}>Elo</div>
          </div>
          <div style={kpiTileStyle}>
            <div style={kpiValueStyle}>{formatPct(overview?.winrate)}</div>
            <div style={kpiLabelStyle}>Winrate</div>
          </div>
          <div style={kpiTileStyle}>
            <div style={kpiValueStyle}>{formatNum(overview?.total_games)}</div>
            <div style={kpiLabelStyle}>Totaal partijen</div>
          </div>
        </div>
      </div>

      {/* Weakness report (data-driven aggregation across games) */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>Zwaktes (op basis van analyses)</div>
        <WeaknessReport />
      </div>

      {/* AI Coaching insights */}
      <div style={sectionStyle}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", borderBottom: "1px solid var(--border)", paddingBottom: "8px" }}>
          <span style={{ fontSize: "13px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--fg-secondary)" }}>
            AI Coaching inzichten
          </span>
          <button
            onClick={handleRefreshInsights}
            disabled={refreshLoading || insightsLoading}
            style={{
              background: (refreshLoading || insightsLoading) ? "var(--bg-secondary)" : "var(--bg-secondary)",
              color: (refreshLoading || insightsLoading) ? "var(--fg-secondary)" : "var(--fg)",
              border: "1px solid var(--border)",
              padding: "5px 12px",
              fontSize: "12px",
              cursor: (refreshLoading || insightsLoading) ? "not-allowed" : "pointer",
              fontFamily: "inherit",
              letterSpacing: "0.02em",
            }}
          >
            {refreshLoading ? "Vernieuwen..." : "Vernieuw inzichten"}
          </button>
        </div>

        {refreshMessage && (
          <p
            style={{
              fontSize: "13px",
              color: refreshMessage.includes("mislukt") ? "var(--danger)" : "var(--fg-secondary)",
              marginBottom: "12px",
            }}
          >
            {refreshMessage}
          </p>
        )}

        {insightsLoading ? (
          <p style={{ color: "var(--fg-secondary)", fontSize: "14px" }}>Inzichten laden...</p>
        ) : insights.length === 0 ? (
          <div
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              padding: "32px",
              textAlign: "center",
            }}
          >
            <p style={{ color: "var(--fg-secondary)", fontSize: "14px", margin: 0 }}>
              Nog geen inzichten. Klik &apos;Vernieuw inzichten&apos; om AI-coaching te genereren.
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {insights.map((insight) => (
              <div
                key={insight.id}
                style={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                  borderLeft: `4px solid ${insightBorderColor(insight.type)}`,
                  padding: "16px 20px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      color: insightBadgeColor(insight.type),
                      border: `1px solid ${insightBadgeColor(insight.type)}`,
                      padding: "1px 6px",
                    }}
                  >
                    {insightTypeBadge(insight.type)}
                  </span>
                  <span style={{ fontSize: "11px", color: "var(--fg-secondary)" }}>
                    Ernst: {severityLabel(insight.severity)}
                  </span>
                </div>
                <p style={{ fontSize: "15px", fontWeight: 700, margin: "0 0 6px 0" }}>
                  {insight.title}
                </p>
                <p style={{ fontSize: "14px", color: "var(--fg-secondary)", margin: "0 0 10px 0", lineHeight: 1.5 }}>
                  {insight.description}
                </p>
                <p style={{ fontSize: "11px", color: "var(--fg-secondary)", margin: 0, opacity: 0.7 }}>
                  Gegenereerd door {insight.model_version}
                  {insight.generated_at ? ` · ${formatDate(insight.generated_at)}` : ""}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Connected accounts */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>Gekoppelde accounts</div>
        {connectedAccounts.length === 0 ? (
          <div
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              padding: "24px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "16px",
              flexWrap: "wrap",
            }}
          >
            <p style={{ color: "var(--fg-secondary)", fontSize: "14px", margin: 0 }}>
              Geen schaakaccounts gekoppeld. Koppel een account om partijen te importeren.
            </p>
            <Link
              href="/settings"
              style={{
                border: "1px solid var(--border)",
                background: "var(--accent)",
                color: "var(--bg)",
                padding: "8px 16px",
                fontSize: "14px",
                display: "inline-block",
              }}
            >
              Account koppelen
            </Link>
          </div>
        ) : (
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            {connectedAccounts.map((acc) => (
              <div
                key={`${acc.platform}-${acc.username}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                  padding: "12px 16px",
                }}
              >
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    background: "var(--fg)",
                    color: "var(--bg)",
                    padding: "2px 7px",
                  }}
                >
                  {acc.platform}
                </span>
                <span style={{ fontSize: "14px", fontWeight: 500 }}>{acc.username}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent games */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>Recente partijen</div>
        {recentGames.length === 0 ? (
          <div
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              padding: "32px",
              textAlign: "center",
              color: "var(--fg-secondary)",
              fontSize: "14px",
            }}
          >
            Geen partijen gevonden. Synchroniseer je account om partijen te laden.
          </div>
        ) : (
          <div style={{ border: "1px solid var(--border)" }}>
            {recentGames.map((game, i) => {
              const { label: resLabel, color: resColor } = getResultLabel(game);
              return (
                <div
                  key={game.id}
                  onClick={() => router.push(`/games/${game.id}`)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "16px",
                    padding: "12px 16px",
                    borderBottom: i < recentGames.length - 1 ? "1px solid var(--border)" : "none",
                    cursor: "pointer",
                    background: "var(--bg)",
                    transition: "background 0.1s",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLDivElement).style.background = "var(--bg-secondary)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLDivElement).style.background = "var(--bg)";
                  }}
                >
                  <span
                    style={{
                      minWidth: "60px",
                      fontWeight: 700,
                      fontSize: "13px",
                      color: resColor,
                    }}
                  >
                    {resLabel}
                  </span>
                  <span style={{ flex: 1, fontSize: "14px", fontWeight: 500 }}>
                    {getOpponent(game)}
                  </span>
                  {game.time_category && (
                    <span
                      style={{
                        border: "1px solid var(--border)",
                        padding: "2px 8px",
                        fontSize: "11px",
                        color: "var(--fg-secondary)",
                        textTransform: "capitalize",
                      }}
                    >
                      {game.time_category}
                    </span>
                  )}
                  <span
                    style={{
                      fontSize: "13px",
                      color: "var(--fg-secondary)",
                      whiteSpace: "nowrap",
                      minWidth: "90px",
                      textAlign: "right",
                    }}
                  >
                    {formatDate(game.played_at)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
        {recentGames.length > 0 && (
          <div style={{ marginTop: "12px", textAlign: "right" }}>
            <Link
              href="/games"
              style={{
                fontSize: "13px",
                color: "var(--fg-secondary)",
                textDecoration: "underline",
              }}
            >
              Alle partijen bekijken →
            </Link>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
        <button
          onClick={handleSync}
          disabled={syncLoading}
          style={{
            background: syncLoading ? "var(--bg-secondary)" : "var(--accent)",
            color: syncLoading ? "var(--fg-secondary)" : "var(--bg)",
            border: "1px solid var(--border)",
            padding: "10px 20px",
            fontSize: "14px",
            cursor: syncLoading ? "not-allowed" : "pointer",
            borderRadius: 0,
            fontFamily: "inherit",
          }}
        >
          {syncLoading ? "Synchroniseren..." : "Synchroniseer partijen"}
        </button>
        <Link
          href="/dashboard"
          style={{
            border: "1px solid var(--border)",
            padding: "10px 20px",
            fontSize: "14px",
            display: "inline-block",
            background: "var(--bg-secondary)",
            color: "var(--fg)",
          }}
        >
          Ga naar Dashboard
        </Link>
        {syncMessage && (
          <p
            style={{
              fontSize: "13px",
              color: syncMessage.includes("mislukt") ? "var(--danger)" : "var(--success)",
              margin: 0,
            }}
          >
            {syncMessage}
          </p>
        )}
      </div>
    </main>
  );
}
