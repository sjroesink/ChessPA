"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Chess } from "chess.js";
import ChessBoard from "@/components/ChessBoard";
import EvalBar from "@/components/EvalBar";
import PieceIcon, { pieceFromSan, stripSanPiece } from "@/components/PieceIcon";
import MoveComment from "@/components/MoveComment";
import MotifBadge from "@/components/MotifBadge";
import AccuracyChart from "@/components/AccuracyChart";
import { useGameAnalysis } from "@/hooks/useGameAnalysis";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Game = {
  id: string;
  white_username: string;
  black_username: string;
  user_color: "white" | "black";
  result: string; // "win" | "loss" | "draw"
  opening_name: string;
  time_category: string;
  user_elo: number;
  opponent_elo: number;
  played_at: string;
  pgn: string;
};

type MultiPV = {
  rank: number;
  san: string;
  uci: string;
  eval_cp: number;
  pv_san: string[];
};

type Motif = {
  type: string;
  attacker?: string;
  pinned?: string;
  target?: string;
  front?: string;
  back?: string;
  square?: string;
  squares?: string[];
};

type MaiaInfo = {
  top1_san?: string | null;
  top1_prob?: number | null;
  match_played?: boolean | null;
  rating_used?: number | null;
};

type MoveAnalysis = {
  move_number: number;
  color: "white" | "black";
  san: string;
  move_san?: string;
  best_move_san?: string;
  eval_before: number;
  eval_after: number;
  classification: string;
  comment?: string | null;
  win_percent_before?: number | null;
  win_percent_after?: number | null;
  accuracy_percent?: number | null;
  is_critical_moment?: boolean | null;
  maia?: MaiaInfo | null;
  details?: {
    multipv?: MultiPV[];
    motifs?: Motif[];
    features?: Record<string, unknown>;
  };
};

const CLASSIFICATION_COLORS: Record<string, string> = {
  best: "var(--success)",
  good: "var(--fg-secondary)",
  inaccuracy: "var(--warning)",
  mistake: "#e67e22",
  blunder: "var(--danger)",
};

const CLASSIFICATION_LABELS: Record<string, string> = {
  best: "Beste",
  good: "Goed",
  inaccuracy: "Onnauwkeurig",
  mistake: "Fout",
  blunder: "Blunder",
};

const CLASSIFICATION_SYMBOLS: Record<string, string> = {
  best: "!",
  good: "",
  inaccuracy: "?!",
  mistake: "?",
  blunder: "??",
};

function getResultLabel(game: Game): { label: string; color: string } {
  if (game.result === "draw") return { label: "Remise", color: "var(--fg-secondary)" };
  if (game.result === "win") return { label: "Winst", color: "var(--success)" };
  return { label: "Verlies", color: "var(--danger)" };
}

export default function GameDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const id = params.id as string;

  const initialMove = Number(searchParams.get("move")) || 0;

  const [game, setGame] = useState<Game | null>(null);
  const [positions, setPositions] = useState<string[]>([]);
  const [moveIndex, setMoveIndexState] = useState(initialMove);

  // Live analysis via WebSocket (merges with REST snapshot on mount).
  const {
    analysis: liveAnalysis,
    summary,
    stageProgress,
    status: wsStatus,
    setFocus,
    requestDeepAll,
  } = useGameAnalysis(id);
  const analysis = liveAnalysis.length > 0 ? (liveAnalysis as MoveAnalysis[]) : null;

  // Wrap setMoveIndex so URL + WS focus stay in sync
  const setMoveIndex = useCallback(
    (val: number | ((prev: number) => number)) => {
      setMoveIndexState((prev) => {
        const next = typeof val === "function" ? val(prev) : val;
        const url = next === 0 ? `/games/${id}` : `/games/${id}?move=${next}`;
        router.replace(url, { scroll: false });
        // next===0 = initial position (no ply yet); send next-1 as focus target for the played ply
        if (next > 0) setFocus(next - 1);
        return next;
      });
    },
    [id, router, setFocus]
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Parse PGN into positions
  const parsePgn = useCallback((pgn: string): { positions: string[]; history: { san: string; from: string; to: string }[] } => {
    const chess = new Chess();
    chess.loadPgn(pgn);
    const history = chess.history({ verbose: true });

    const positionList: string[] = [
      "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    ];
    const replay = new Chess();
    for (const move of history) {
      replay.move(move.san);
      positionList.push(replay.fen());
    }

    return { positions: positionList, history };
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);

    fetch(`${API_URL}/api/games/${id}`, { credentials: "include" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((gameData: Game) => {
        setGame(gameData);
        if (gameData.pgn) {
          const { positions: pos } = parsePgn(gameData.pgn);
          setPositions(pos);
          const clamped = Math.max(0, Math.min(initialMove, pos.length - 1));
          setMoveIndexState(clamped);
          if (clamped > 0) setFocus(clamped - 1);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, parsePgn, initialMove, setFocus]);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") {
        setMoveIndex((i) => Math.max(0, i - 1));
      } else if (e.key === "ArrowRight") {
        setMoveIndex((i) => Math.min(positions.length - 1, i + 1));
      } else if (e.key === "Home") {
        setMoveIndex(0);
      } else if (e.key === "End") {
        setMoveIndex(positions.length - 1);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [positions.length]);

  // Get eval for current position, normalised to White's perspective.
  // Stored eval_after is from the mover's (STM) perspective.
  const currentEval = (): number => {
    if (!analysis || moveIndex === 0) return 0;
    const move = analysis[moveIndex - 1];
    if (!move) return 0;
    const stm = move.eval_after ?? 0;
    return move.color === "white" ? stm : -stm;
  };

  // Squares to highlight for the last played move (chess.com style)
  const lastMoveHighlights = (): { square: string; color: string }[] => {
    if (moveIndex === 0) return [];
    const beforeFen = positions[moveIndex - 1];
    if (!beforeFen) return [];
    try {
      const chess = new Chess(beforeFen);
      // Find which move was actually played (from history)
      const full = new Chess();
      if (game?.pgn) full.loadPgn(game.pgn);
      const hist = full.history({ verbose: true });
      const played = hist[moveIndex - 1];
      if (!played) return [];

      const cls = analysis?.[moveIndex - 1]?.classification;
      const badColor = "rgba(235, 97, 80, 0.55)"; // red for bad moves
      const okColor = "rgba(255, 241, 128, 0.55)"; // yellow for normal highlight
      const color = cls === "blunder" || cls === "mistake" ? badColor : okColor;
      return [
        { square: played.from, color },
        { square: played.to, color },
      ];
    } catch {
      return [];
    }
  };

  // Classification badge on the played "to" square (chess.com-style symbol bubble)
  const classificationBadges = (): { square: string; symbol: string; color: string; title?: string }[] => {
    if (!analysis || moveIndex === 0) return [];
    const m = analysis[moveIndex - 1];
    if (!m) return [];
    const cls = m.classification;
    const symbol = CLASSIFICATION_SYMBOLS[cls];
    if (!symbol) return [];
    const bg = cls === "blunder" ? "#d33" : cls === "mistake" ? "#e67e22" : cls === "inaccuracy" ? "#dab025" : cls === "best" ? "#22a06b" : null;
    if (!bg) return [];
    try {
      const beforeFen = positions[moveIndex - 1];
      if (!beforeFen) return [];
      const chess = new Chess();
      if (game?.pgn) chess.loadPgn(game.pgn);
      const hist = chess.history({ verbose: true });
      const played = hist[moveIndex - 1];
      if (!played) return [];
      return [{
        square: played.to,
        symbol,
        color: bg,
        title: CLASSIFICATION_LABELS[cls] || cls,
      }];
    } catch {
      return [];
    }
  };

  // Compute arrow for the best move when viewing a sub-optimal move
  const bestMoveArrow = (): { startSquare: string; endSquare: string; color?: string }[] => {
    if (!analysis || moveIndex === 0) return [];
    const m = analysis[moveIndex - 1];
    if (!m || !m.best_move_san) return [];
    if (m.classification === "best" || m.classification === "good") return [];
    if (m.move_san === m.best_move_san) return [];
    const beforeFen = positions[moveIndex - 1];
    if (!beforeFen) return [];
    try {
      const chess = new Chess(beforeFen);
      const mv = chess.move(m.best_move_san);
      if (!mv) return [];
      return [{ startSquare: mv.from, endSquare: mv.to, color: "rgba(34, 197, 94, 0.75)" }];
    } catch {
      return [];
    }
  };

  if (loading) {
    return (
      <main style={{ padding: "32px", maxWidth: "1200px", margin: "0 auto" }}>
        <p style={{ color: "var(--fg-secondary)" }}>Laden...</p>
      </main>
    );
  }

  if (error || !game) {
    return (
      <main style={{ padding: "32px", maxWidth: "1200px", margin: "0 auto" }}>
        <p style={{ color: "var(--danger)" }}>Fout: {error || "Partij niet gevonden"}</p>
      </main>
    );
  }

  const { label: resLabel, color: resColor } = getResultLabel(game);

  // Build move list from PGN
  const chess = new Chess();
  let history: { san: string }[] = [];
  if (game.pgn) {
    chess.loadPgn(game.pgn);
    history = chess.history({ verbose: true });
  }

  const navBtnStyle: React.CSSProperties = {
    background: "var(--bg-secondary)",
    color: "var(--fg)",
    border: "1px solid var(--border)",
    padding: "8px 14px",
    fontSize: "16px",
    cursor: "pointer",
    borderRadius: 0,
    fontFamily: "inherit",
    minWidth: "40px",
  };

  return (
    <main style={{ padding: "32px", maxWidth: "1200px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "24px", fontWeight: 600, marginBottom: "8px" }}>
          {game.white_username} vs {game.black_username}
        </h1>
        <div
          style={{
            display: "flex",
            gap: "16px",
            alignItems: "center",
            fontSize: "14px",
            color: "var(--fg-secondary)",
            flexWrap: "wrap",
          }}
        >
          <span style={{ color: resColor, fontWeight: 600 }}>{resLabel}</span>
          {game.opening_name && <span>{game.opening_name}</span>}
          <span
            style={{
              border: "1px solid var(--border)",
              padding: "2px 8px",
              fontSize: "12px",
              textTransform: "capitalize",
            }}
          >
            {game.time_category}
          </span>
          <span>Elo: {game.user_elo}</span>
        </div>
      </div>

      {/* Main layout */}
      <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>
        {/* Left: Board + nav */}
        <div>
          {(() => {
            const isUserWhite = game.user_color === "white";
            const topName = isUserWhite ? game.black_username : game.white_username;
            const topElo = isUserWhite ? game.opponent_elo : game.user_elo;
            const bottomName = isUserWhite ? game.white_username : game.black_username;
            const bottomElo = isUserWhite ? game.user_elo : game.opponent_elo;
            const nameBarStyle: React.CSSProperties = {
              display: "flex",
              gap: "10px",
              alignItems: "center",
              padding: "6px 10px",
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
              fontSize: "14px",
              width: "400px",
              marginLeft: analysis ? "30px" : "0",
            };
            return (
              <>
                <div style={nameBarStyle}>
                  <strong>{topName || "?"}</strong>
                  {topElo && <span style={{ color: "var(--fg-secondary)" }}>({topElo})</span>}
                </div>
                <div style={{ display: "flex", height: "400px" }}>
                  {analysis && <EvalBar value={currentEval()} />}
                  <ChessBoard
                    position={positions[moveIndex] || "start"}
                    orientation={game.user_color}
                    width={400}
                    arrows={bestMoveArrow()}
                    highlightedSquares={lastMoveHighlights()}
                    badges={classificationBadges()}
                  />
                </div>
                <div style={nameBarStyle}>
                  <strong>{bottomName || "?"}</strong>
                  {bottomElo && <span style={{ color: "var(--fg-secondary)" }}>({bottomElo})</span>}
                </div>
              </>
            );
          })()}

          {/* Summary bar: accuracy, opening, phase ACPL */}
          {summary && (
            <div
              style={{
                marginTop: 12,
                padding: "8px 12px",
                border: "1px solid var(--border)",
                background: "var(--bg-secondary)",
                display: "flex",
                flexDirection: "column",
                gap: 6,
                fontSize: 12,
              }}
            >
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                {summary.accuracy_white != null && (
                  <span>
                    <strong>Wit</strong> {summary.accuracy_white.toFixed(0)}%
                  </span>
                )}
                {summary.accuracy_black != null && (
                  <span>
                    <strong>Zwart</strong> {summary.accuracy_black.toFixed(0)}%
                  </span>
                )}
                {summary.opening_eco && (
                  <span>
                    <strong>{summary.opening_eco}</strong> {summary.opening_name}
                  </span>
                )}
              </div>
              {summary.phase_acpl && <AccuracyChart phaseAcpl={summary.phase_acpl} />}
            </div>
          )}

          {/* Navigation buttons */}
          <div
            style={{
              display: "flex",
              gap: "8px",
              marginTop: "12px",
            }}
          >
            <button
              onClick={() => setMoveIndex(0)}
              disabled={moveIndex === 0}
              style={navBtnStyle}
              title="Begin"
            >
              &#x23EE;
            </button>
            <button
              onClick={() => setMoveIndex((i) => Math.max(0, i - 1))}
              disabled={moveIndex === 0}
              style={navBtnStyle}
              title="Vorige zet"
            >
              &#x25C0;
            </button>
            <button
              onClick={() => setMoveIndex((i) => Math.min(positions.length - 1, i + 1))}
              disabled={moveIndex >= positions.length - 1}
              style={navBtnStyle}
              title="Volgende zet"
            >
              &#x25B6;
            </button>
            <button
              onClick={() => setMoveIndex(positions.length - 1)}
              disabled={moveIndex >= positions.length - 1}
              style={navBtnStyle}
              title="Einde"
            >
              &#x23ED;
            </button>
            <span
              style={{
                marginLeft: "auto",
                fontSize: "13px",
                color: "var(--fg-secondary)",
                alignSelf: "center",
              }}
            >
              Zet {moveIndex} / {positions.length - 1}
            </span>
          </div>

          {/* Commentary panel */}
          {moveIndex > 0 && analysis?.[moveIndex - 1] && (() => {
            const m = analysis[moveIndex - 1];
            const cls = m.classification;
            const showAsError = cls === "blunder" || cls === "mistake" || cls === "inaccuracy";
            const borderColor = CLASSIFICATION_COLORS[cls] || "var(--border)";
            return (
              <div
                style={{
                  marginTop: "16px",
                  border: `1px solid ${borderColor}`,
                  padding: "12px 14px",
                  width: "400px",
                  background: "var(--bg-secondary)",
                }}
              >
                <div style={{ display: "flex", gap: "10px", alignItems: "center", marginBottom: "8px", flexWrap: "wrap" }}>
                  <span style={{ fontSize: "13px", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: "4px" }}>
                    {m.move_number}.{m.color === "white" ? "" : " ..."}
                    <PieceIcon piece={pieceFromSan(m.move_san ?? "")} color={m.color} size={16} />
                    {stripSanPiece(m.move_san ?? "")}
                  </span>
                  {CLASSIFICATION_SYMBOLS[cls] && (
                    <span
                      title={CLASSIFICATION_LABELS[cls] || cls}
                      style={{
                        fontSize: "16px",
                        fontWeight: 700,
                        color: borderColor,
                        cursor: "help",
                      }}
                    >
                      {CLASSIFICATION_SYMBOLS[cls]}
                    </span>
                  )}
                  {showAsError && m.best_move_san && m.best_move_san !== m.move_san && (
                    <span style={{ fontSize: "12px", color: "var(--fg-secondary)", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                      Beste:{" "}
                      <PieceIcon piece={pieceFromSan(m.best_move_san)} color={m.color} size={14} />
                      <strong style={{ color: "var(--success)" }}>{stripSanPiece(m.best_move_san)}</strong>
                    </span>
                  )}
                </div>
                {m.comment ? (
                  <MoveComment text={m.comment} color={m.color} />
                ) : showAsError ? (
                  <p style={{ fontSize: "12px", color: "var(--fg-secondary)", fontStyle: "italic", margin: 0 }}>
                    Commentaar wordt gegenereerd...
                  </p>
                ) : null}

                {/* Rich facts: accuracy/win%, maia trap, motifs, multipv */}
                {(() => {
                  const drop =
                    typeof m.win_percent_before === "number" && typeof m.win_percent_after === "number"
                      ? m.win_percent_before - m.win_percent_after
                      : null;
                  const motifs = m.details?.motifs || [];
                  const multipv = m.details?.multipv || [];
                  const showMaiaTrap =
                    m.maia?.match_played &&
                    (cls === "blunder" || cls === "mistake");
                  const hasExtra =
                    drop != null ||
                    motifs.length > 0 ||
                    multipv.length > 1 ||
                    m.is_critical_moment ||
                    showMaiaTrap;
                  if (!hasExtra) return null;
                  return (
                    <div style={{ marginTop: 8, fontSize: 12, display: "flex", flexDirection: "column", gap: 4 }}>
                      {(drop != null || m.accuracy_percent != null) && (
                        <div style={{ color: "var(--fg-secondary)" }}>
                          {m.accuracy_percent != null && <>Acc {m.accuracy_percent.toFixed(0)}%</>}
                          {drop != null && <> · ΔWin {drop.toFixed(0)}%</>}
                        </div>
                      )}
                      {m.is_critical_moment && (
                        <div style={{ color: "#b45309" }}>Kritiek moment</div>
                      )}
                      {showMaiaTrap && (
                        <div style={{ color: "#0369a1" }}>
                          Menselijke valstrik (Maia-{m.maia?.rating_used ?? "?"})
                        </div>
                      )}
                      {motifs.length > 0 && (
                        <div>
                          {motifs.map((mo, i) => (
                            <MotifBadge key={i} motif={mo} />
                          ))}
                        </div>
                      )}
                      {multipv.length > 1 && (
                        <details>
                          <summary style={{ cursor: "pointer", color: "var(--fg-secondary)" }}>
                            Alternatieven
                          </summary>
                          <ul style={{ margin: "4px 0 0 16px", padding: 0, listStyle: "none", fontFamily: "monospace" }}>
                            {multipv.map((pv) => (
                              <li key={pv.rank} style={{ display: "flex", gap: 6 }}>
                                <span style={{ color: "var(--fg-secondary)" }}>#{pv.rank}</span>
                                <span style={{ flex: 1 }}>{pv.pv_san.slice(0, 5).join(" ")}</span>
                                <span>{(pv.eval_cp / 100).toFixed(2)}</span>
                              </li>
                            ))}
                          </ul>
                        </details>
                      )}
                    </div>
                  );
                })()}
              </div>
            );
          })()}
        </div>

        {/* Right: Move list */}
        <div
          style={{
            flex: 1,
            minWidth: "260px",
            border: "1px solid var(--border)",
            maxHeight: "460px",
            overflowY: "auto",
          }}
        >
          <div
            style={{
              padding: "10px 14px",
              borderBottom: "1px solid var(--border)",
              background: "var(--bg-secondary)",
              fontWeight: 600,
              fontSize: "14px",
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            <span>Zetten</span>
            <span style={{ fontSize: 11, color: "var(--fg-secondary)", fontWeight: 400 }}>
              {wsStatus === "open"
                ? "live"
                : wsStatus === "connecting"
                  ? "verbinden…"
                  : wsStatus === "error"
                    ? "offline"
                    : ""}
            </span>
            <button
              onClick={() => requestDeepAll()}
              title="Laat de achtergrond-analyse het hele potje diep analyseren"
              style={{
                marginLeft: "auto",
                fontSize: 11,
                padding: "2px 8px",
                border: "1px solid var(--border)",
                background: "var(--bg)",
                color: "var(--fg-secondary)",
                cursor: "pointer",
              }}
            >
              Diepe analyse
            </button>
          </div>
          {stageProgress.total > 0 && (
            <div
              style={{
                padding: "6px 14px",
                borderBottom: "1px solid var(--border)",
                display: "flex",
                gap: 12,
                fontSize: 11,
                color: "var(--fg-secondary)",
                flexWrap: "wrap",
              }}
            >
              {(["shallow", "standard", "deep", "enrich"] as const).map((s) => {
                const done = stageProgress[s];
                const pct = stageProgress.total ? Math.round((done / stageProgress.total) * 100) : 0;
                return (
                  <span key={s} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                    <span style={{ textTransform: "capitalize" }}>{s}</span>
                    <span>{pct}%</span>
                  </span>
                );
              })}
            </div>
          )}
          <div style={{ padding: "8px" }}>
            {history.length === 0 && (
              <p style={{ color: "var(--fg-secondary)", fontSize: "14px", padding: "8px" }}>
                Geen zetten beschikbaar.
              </p>
            )}
            {/* Render moves in pairs (white + black) */}
            {Array.from({ length: Math.ceil(history.length / 2) }).map((_, rowIdx) => {
              const whiteIdx = rowIdx * 2;
              const blackIdx = rowIdx * 2 + 1;
              const whiteMove = history[whiteIdx];
              const blackMove = blackIdx < history.length ? history[blackIdx] : null;
              const moveNum = rowIdx + 1;

              const whiteAnalysis = analysis?.[whiteIdx];
              const blackAnalysis = blackIdx < history.length ? analysis?.[blackIdx] : null;

              return (
                <div
                  key={rowIdx}
                  style={{
                    display: "flex",
                    fontSize: "14px",
                    borderBottom:
                      rowIdx < Math.ceil(history.length / 2) - 1
                        ? "1px solid var(--border)"
                        : undefined,
                  }}
                >
                  {/* Move number */}
                  <span
                    style={{
                      width: "36px",
                      padding: "6px 4px",
                      color: "var(--fg-secondary)",
                      fontSize: "12px",
                      textAlign: "right",
                      flexShrink: 0,
                    }}
                  >
                    {moveNum}.
                  </span>

                  {/* White move */}
                  <span
                    onClick={() => setMoveIndex(whiteIdx + 1)}
                    style={{
                      flex: 1,
                      padding: "6px 8px",
                      cursor: "pointer",
                      background: moveIndex === whiteIdx + 1 ? "var(--bg-secondary)" : "transparent",
                      fontWeight: moveIndex === whiteIdx + 1 ? 600 : 400,
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <PieceIcon piece={pieceFromSan(whiteMove.san)} color="white" size={16} />
                    <span>{stripSanPiece(whiteMove.san)}</span>
                    {whiteAnalysis?.classification && CLASSIFICATION_SYMBOLS[whiteAnalysis.classification] && (
                      <span
                        title={CLASSIFICATION_LABELS[whiteAnalysis.classification] || whiteAnalysis.classification}
                        style={{
                          fontSize: "14px",
                          fontWeight: 700,
                          color: CLASSIFICATION_COLORS[whiteAnalysis.classification] || "var(--fg-secondary)",
                          cursor: "help",
                        }}
                      >
                        {CLASSIFICATION_SYMBOLS[whiteAnalysis.classification]}
                      </span>
                    )}
                  </span>

                  {/* Black move */}
                  {blackMove ? (
                    <span
                      onClick={() => setMoveIndex(blackIdx + 1)}
                      style={{
                        flex: 1,
                        padding: "6px 8px",
                        cursor: "pointer",
                        background: moveIndex === blackIdx + 1 ? "var(--bg-secondary)" : "transparent",
                        fontWeight: moveIndex === blackIdx + 1 ? 600 : 400,
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <PieceIcon piece={pieceFromSan(blackMove.san)} color="black" size={16} />
                      <span>{stripSanPiece(blackMove.san)}</span>
                      {blackAnalysis?.classification && CLASSIFICATION_SYMBOLS[blackAnalysis.classification] && (
                        <span
                          title={CLASSIFICATION_LABELS[blackAnalysis.classification] || blackAnalysis.classification}
                          style={{
                            fontSize: "14px",
                            fontWeight: 700,
                            color: CLASSIFICATION_COLORS[blackAnalysis.classification] || "var(--fg-secondary)",
                            cursor: "help",
                          }}
                        >
                          {CLASSIFICATION_SYMBOLS[blackAnalysis.classification]}
                        </span>
                      )}
                    </span>
                  ) : (
                    <span style={{ flex: 1 }} />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </main>
  );
}
