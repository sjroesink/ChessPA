"use client";

export interface Motif {
  type: string;
  attacker?: string;
  pinned?: string;
  target?: string;
  front?: string;
  back?: string;
  square?: string;
  squares?: string[];
  verified_gain_cp?: number;
}

const LABELS: Record<string, string> = {
  fork: "Vork",
  absolute_pin: "Absolute penning",
  relative_pin: "Penning",
  skewer: "Spies",
  hanging: "Hangend stuk",
  discovered_attack: "Aftrekaanval",
};

const COLORS: Record<string, string> = {
  fork: "#d97706",
  absolute_pin: "#b91c1c",
  relative_pin: "#ea580c",
  skewer: "#9333ea",
  hanging: "#0369a1",
  discovered_attack: "#be123c",
};

export default function MotifBadge({ motif }: { motif: Motif }) {
  const color = COLORS[motif.type] || "#555";
  const label = LABELS[motif.type] || motif.type;
  const title =
    motif.type === "hanging"
      ? `Hangend stuk op ${motif.square ?? "?"}`
      : motif.type === "fork"
        ? `Vork van ${motif.attacker ?? "?"} op ${(motif.squares || []).join(", ")}`
        : motif.type.includes("pin")
          ? `${label}: ${motif.pinned ?? "?"} → ${motif.target ?? "?"}`
          : motif.type === "skewer"
            ? `Spies: ${motif.front ?? "?"} → ${motif.back ?? "?"}`
            : label;
  return (
    <span
      title={title}
      style={{
        display: "inline-block",
        padding: "1px 6px",
        fontSize: 11,
        fontWeight: 600,
        border: `1px solid ${color}`,
        color,
        background: "transparent",
        marginRight: 4,
        borderRadius: 0,
      }}
    >
      {label}
    </span>
  );
}
