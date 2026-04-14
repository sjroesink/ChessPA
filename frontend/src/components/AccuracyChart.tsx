"use client";

interface Props {
  phaseAcpl: Record<string, number> | null | undefined;
}

const PHASE_LABEL: Record<string, string> = {
  opening: "Opening",
  middlegame: "Middenspel",
  endgame: "Eindspel",
};

const PHASE_ORDER = ["opening", "middlegame", "endgame"];

export default function AccuracyChart({ phaseAcpl }: Props) {
  if (!phaseAcpl) return null;
  const entries = PHASE_ORDER.filter((p) => p in phaseAcpl).map((p) => [p, phaseAcpl[p]] as const);
  if (entries.length === 0) return null;
  const max = Math.max(...entries.map(([, v]) => v), 1);
  return (
    <div style={{ fontSize: 12 }}>
      {entries.map(([phase, cpl]) => (
        <div
          key={phase}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            margin: "2px 0",
          }}
        >
          <span style={{ width: 90 }}>{PHASE_LABEL[phase] ?? phase}</span>
          <div style={{ flex: 1, height: 8, background: "var(--border)" }}>
            <div
              style={{
                width: `${(cpl / max) * 100}%`,
                height: "100%",
                background: "#b45309",
              }}
            />
          </div>
          <span style={{ width: 56, textAlign: "right" }}>{cpl.toFixed(0)} cpl</span>
        </div>
      ))}
    </div>
  );
}
