"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { Chess } from "chess.js";
import ChessBoard from "@/components/ChessBoard";
import EvalBar from "@/components/EvalBar";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Game = {
  id: number;
  white: string;
  black: string;
  user_color: "white" | "black";
  result: string;
  opening_name: string;
  time_category: string;
  user_elo: number;
  played_at: string;
  pgn: string;
};

type MoveAnalysis = {
  move_number: number;
  color: "white" | "black";
  san: string;
  eval_before: number;
  eval_after: number;
  classification: string;
};

type AnalysisResponse = {
  moves: MoveAnalysis[];
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

export default function GameDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [game, setGame] = useState<Game | null>(null);
  const [analysis, setAnalysis] = useState<MoveAnalysis[] | null>(null);
  const [positions, setPositions] = useState<string[]>([]);
  const [moveIndex, setMoveIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Parse PGN into positions
  const parsePgn = useCallback((pgn: string): { positions: string[]; history: { san: string }[] } => {
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

    const fetchGame = fetch(`${API_URL}/api/games/${id}`, {
      credentials: "include",
    }).then((res) => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    });

    const fetchAnalysis = fetch(`${API_URL}/api/games/${id}/analysis`, {
      credentials: "include",
    })
      .then((res) => {
        if (!res.ok) return null;
        return res.json();
      })
      .catch(() => null);

    Promise.all([fetchGame, fetchAnalysis])
      .then(([gameData, analysisData]: [Game, AnalysisResponse | null]) => {
        setGame(gameData);
        if (analysisData?.moves) {
          setAnalysis(analysisData.moves);
        }

        if (gameData.pgn) {
          const { positions: pos } = parsePgn(gameData.pgn);
          setPositions(pos);
          setMoveIndex(0);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, parsePgn]);

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

  // Get eval for current position
  const currentEval = (): number => {
    if (!analysis || moveIndex === 0) return 0;
    const move = analysis[moveIndex - 1];
    return move?.eval_after ?? 0;
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
          {game.white} vs {game.black}
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
          <div style={{ display: "flex", height: "400px" }}>
            {analysis && <EvalBar value={currentEval()} />}
            <ChessBoard
              position={positions[moveIndex] || "start"}
              orientation={game.user_color}
              width={400}
            />
          </div>

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
            }}
          >
            Zetten
          </div>
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
                    {whiteMove.san}
                    {whiteAnalysis?.classification && (
                      <span
                        style={{
                          fontSize: "11px",
                          padding: "1px 5px",
                          border: `1px solid ${CLASSIFICATION_COLORS[whiteAnalysis.classification] || "var(--border)"}`,
                          color: CLASSIFICATION_COLORS[whiteAnalysis.classification] || "var(--fg-secondary)",
                        }}
                      >
                        {CLASSIFICATION_LABELS[whiteAnalysis.classification] || whiteAnalysis.classification}
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
                      {blackMove.san}
                      {blackAnalysis?.classification && (
                        <span
                          style={{
                            fontSize: "11px",
                            padding: "1px 5px",
                            border: `1px solid ${CLASSIFICATION_COLORS[blackAnalysis.classification] || "var(--border)"}`,
                            color: CLASSIFICATION_COLORS[blackAnalysis.classification] || "var(--fg-secondary)",
                          }}
                        >
                          {CLASSIFICATION_LABELS[blackAnalysis.classification] || blackAnalysis.classification}
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
