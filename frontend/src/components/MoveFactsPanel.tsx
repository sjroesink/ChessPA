"use client";
import MotifBadge, { type Motif } from "./MotifBadge";
import PieceIcon, { pieceFromSan } from "./PieceIcon";
import MoveComment from "./MoveComment";

interface MultiPV {
  rank: number;
  san: string;
  eval_cp: number;
  pv_san: string[];
}

interface MaiaInfo {
  top1_san?: string | null;
  top1_prob?: number | null;
  match_played?: boolean | null;
  rating_used?: number | null;
}

interface Props {
  moveSan: string;
  color: "white" | "black";
  classification: string;
  winBefore?: number | null;
  winAfter?: number | null;
  accuracy?: number | null;
  cpl?: number | null;
  isCritical?: boolean | null;
  multipv?: MultiPV[];
  motifs?: Motif[];
  maia?: MaiaInfo | null;
  commentary?: string | null;
}

export default function MoveFactsPanel({
  moveSan,
  color,
  classification,
  winBefore,
  winAfter,
  accuracy,
  cpl,
  isCritical,
  multipv,
  motifs,
  maia,
  commentary,
}: Props) {
  const drop =
    typeof winBefore === "number" && typeof winAfter === "number"
      ? winBefore - winAfter
      : null;
  const showMaiaTrap =
    maia?.match_played && (classification === "blunder" || classification === "mistake");

  return (
    <div style={{ border: "1px solid var(--border)", padding: 8, fontSize: 13 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <PieceIcon piece={pieceFromSan(moveSan)} color={color} size={16} />
        <strong style={{ fontFamily: "monospace" }}>{moveSan}</strong>
        <span style={{ marginLeft: "auto", color: "var(--muted, #666)", fontSize: 12 }}>
          {accuracy != null ? `Acc ${accuracy.toFixed(0)}%` : ""}
          {cpl != null ? ` · CPL ${cpl.toFixed(0)}` : ""}
          {drop != null ? ` · ΔWin ${drop.toFixed(0)}%` : ""}
        </span>
      </div>
      {isCritical && (
        <div style={{ fontSize: 11, color: "#b45309", marginBottom: 4 }}>Kritiek moment</div>
      )}
      {showMaiaTrap && (
        <div style={{ fontSize: 11, color: "#0369a1", marginBottom: 4 }}>
          Menselijke valstrik (Maia-{maia?.rating_used ?? "?"} voorspelde exact deze zet)
        </div>
      )}
      {motifs && motifs.length > 0 && (
        <div style={{ margin: "4px 0" }}>
          {motifs.map((m, i) => (
            <MotifBadge key={i} motif={m} />
          ))}
        </div>
      )}
      {commentary && (
        <div style={{ margin: "6px 0" }}>
          <MoveComment text={commentary} color={color} />
        </div>
      )}
      {multipv && multipv.length > 1 && (
        <details style={{ marginTop: 4 }}>
          <summary style={{ cursor: "pointer", fontSize: 12, color: "var(--muted, #666)" }}>
            Alternatieven
          </summary>
          <ul
            style={{
              margin: "4px 0 0 16px",
              padding: 0,
              listStyle: "none",
              fontFamily: "monospace",
              fontSize: 12,
            }}
          >
            {multipv.map((pv) => (
              <li key={pv.rank} style={{ display: "flex", gap: 6 }}>
                <span style={{ color: "var(--muted, #888)" }}>#{pv.rank}</span>
                <span style={{ flex: 1 }}>{pv.pv_san.slice(0, 5).join(" ")}</span>
                <span>{(pv.eval_cp / 100).toFixed(2)}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
