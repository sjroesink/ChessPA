"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Game = {
  id: number;
  white: string;
  black: string;
  user_color: "white" | "black";
  result: string; // "1-0" | "0-1" | "1/2-1/2"
  opening_name: string;
  time_category: string;
  user_elo: number;
  played_at: string;
};

type GamesResponse = {
  games: Game[];
  total: number;
  page: number;
  page_size: number;
};

const RESULT_OPTIONS = [
  { value: "", label: "Alles" },
  { value: "win", label: "Winst" },
  { value: "loss", label: "Verlies" },
  { value: "draw", label: "Remise" },
];

const TIME_OPTIONS = [
  { value: "", label: "Alles" },
  { value: "bullet", label: "Bullet" },
  { value: "blitz", label: "Blitz" },
  { value: "rapid", label: "Rapid" },
  { value: "classical", label: "Classical" },
];

function getOpponent(game: Game): string {
  return game.user_color === "white" ? game.black : game.white;
}

function getResultLabel(game: Game): { label: string; color: string } {
  const isWhite = game.user_color === "white";
  if (game.result === "1/2-1/2") return { label: "Remise", color: "var(--fg-secondary)" };
  if (
    (isWhite && game.result === "1-0") ||
    (!isWhite && game.result === "0-1")
  ) {
    return { label: "Winst", color: "var(--success)" };
  }
  return { label: "Verlies", color: "var(--danger)" };
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const months = [
    "jan", "feb", "mrt", "apr", "mei", "jun",
    "jul", "aug", "sep", "okt", "nov", "dec",
  ];
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
}

export default function GamesPage() {
  const router = useRouter();
  const [games, setGames] = useState<Game[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [resultFilter, setResultFilter] = useState("");
  const [timeFilter, setTimeFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    if (resultFilter) params.set("result", resultFilter);
    if (timeFilter) params.set("time_category", timeFilter);

    fetch(`${API_URL}/api/games?${params.toString()}`, {
      credentials: "include",
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: GamesResponse) => {
        setGames(data.games);
        setTotal(data.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [page, pageSize, resultFilter, timeFilter]);

  // Reset to page 1 when filters change
  const handleResultFilter = (val: string) => {
    setResultFilter(val);
    setPage(1);
  };

  const handleTimeFilter = (val: string) => {
    setTimeFilter(val);
    setPage(1);
  };

  const totalPages = Math.ceil(total / pageSize);

  const selectStyle: React.CSSProperties = {
    background: "var(--bg-secondary)",
    color: "var(--fg)",
    border: "1px solid var(--border)",
    padding: "6px 10px",
    fontSize: "14px",
    borderRadius: 0,
    cursor: "pointer",
    fontFamily: "inherit",
  };

  return (
    <main style={{ padding: "32px", maxWidth: "1100px", margin: "0 auto" }}>
      {/* Header */}
      <h1
        style={{
          fontSize: "24px",
          fontWeight: 600,
          marginBottom: "24px",
        }}
      >
        Partijen
      </h1>

      {/* Filter bar */}
      <div
        style={{
          display: "flex",
          gap: "12px",
          marginBottom: "20px",
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <label style={{ fontSize: "14px", color: "var(--fg-secondary)" }}>
          Resultaat:
        </label>
        <select
          value={resultFilter}
          onChange={(e) => handleResultFilter(e.target.value)}
          style={selectStyle}
        >
          {RESULT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <label
          style={{
            fontSize: "14px",
            color: "var(--fg-secondary)",
            marginLeft: "8px",
          }}
        >
          Tijdcategorie:
        </label>
        <select
          value={timeFilter}
          onChange={(e) => handleTimeFilter(e.target.value)}
          style={selectStyle}
        >
          {TIME_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {total > 0 && (
          <span
            style={{
              marginLeft: "auto",
              fontSize: "13px",
              color: "var(--fg-secondary)",
            }}
          >
            {total} partij{total !== 1 ? "en" : ""}
          </span>
        )}
      </div>

      {/* States */}
      {loading && (
        <p style={{ color: "var(--fg-secondary)", padding: "32px 0" }}>
          Laden...
        </p>
      )}
      {error && (
        <p style={{ color: "var(--danger)", padding: "16px 0" }}>
          Fout: {error}
        </p>
      )}

      {/* Table */}
      {!loading && !error && games.length === 0 && (
        <p style={{ color: "var(--fg-secondary)", padding: "32px 0" }}>
          Geen partijen gevonden.
        </p>
      )}

      {!loading && !error && games.length > 0 && (
        <div
          style={{
            border: "1px solid var(--border)",
            overflowX: "auto",
          }}
        >
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: "14px",
            }}
          >
            <thead>
              <tr
                style={{
                  background: "var(--bg-secondary)",
                  borderBottom: "1px solid var(--border)",
                }}
              >
                {[
                  "Tegenstander",
                  "Opening",
                  "Resultaat",
                  "Tijdcategorie",
                  "Elo",
                  "Datum",
                ].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: "10px 14px",
                      textAlign: "left",
                      fontWeight: 600,
                      color: "var(--fg)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {games.map((game, i) => {
                const { label: resLabel, color: resColor } = getResultLabel(game);
                return (
                  <tr
                    key={game.id}
                    onClick={() => router.push(`/games/${game.id}`)}
                    style={{
                      borderBottom:
                        i < games.length - 1
                          ? "1px solid var(--border)"
                          : undefined,
                      cursor: "pointer",
                      background: "var(--bg)",
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLTableRowElement).style.background =
                        "var(--bg-secondary)";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLTableRowElement).style.background =
                        "var(--bg)";
                    }}
                  >
                    <td style={{ padding: "10px 14px", fontWeight: 500 }}>
                      {getOpponent(game)}
                    </td>
                    <td
                      style={{
                        padding: "10px 14px",
                        color: "var(--fg-secondary)",
                        maxWidth: "220px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {game.opening_name || "—"}
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <span style={{ color: resColor, fontWeight: 600 }}>
                        {resLabel}
                      </span>
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <span
                        style={{
                          border: "1px solid var(--border)",
                          padding: "2px 8px",
                          fontSize: "12px",
                          color: "var(--fg-secondary)",
                          textTransform: "capitalize",
                        }}
                      >
                        {game.time_category || "—"}
                      </span>
                    </td>
                    <td style={{ padding: "10px 14px" }}>{game.user_elo}</td>
                    <td
                      style={{
                        padding: "10px 14px",
                        color: "var(--fg-secondary)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {formatDate(game.played_at)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div
          style={{
            display: "flex",
            gap: "12px",
            alignItems: "center",
            marginTop: "20px",
          }}
        >
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            style={{
              background: page <= 1 ? "var(--bg-secondary)" : "var(--accent)",
              color: page <= 1 ? "var(--fg-secondary)" : "var(--bg)",
              border: "1px solid var(--border)",
              padding: "8px 16px",
              fontSize: "14px",
              cursor: page <= 1 ? "not-allowed" : "pointer",
              borderRadius: 0,
              fontFamily: "inherit",
            }}
          >
            Vorige
          </button>
          <span style={{ fontSize: "14px", color: "var(--fg-secondary)" }}>
            Pagina {page} van {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            style={{
              background:
                page >= totalPages ? "var(--bg-secondary)" : "var(--accent)",
              color:
                page >= totalPages ? "var(--fg-secondary)" : "var(--bg)",
              border: "1px solid var(--border)",
              padding: "8px 16px",
              fontSize: "14px",
              cursor: page >= totalPages ? "not-allowed" : "pointer",
              borderRadius: 0,
              fontFamily: "inherit",
            }}
          >
            Volgende
          </button>
        </div>
      )}
    </main>
  );
}
