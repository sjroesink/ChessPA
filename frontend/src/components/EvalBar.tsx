"use client";

export default function EvalBar({ value }: { value: number }) {
  // Clamp to -500..500, map to 0..100 percentage for white
  const clamped = Math.max(-500, Math.min(500, value));
  const whitePct = Math.round(50 + (clamped / 500) * 50);

  return (
    <div style={{
      width: "24px",
      height: "100%",
      display: "flex",
      flexDirection: "column",
      border: "1px solid var(--border)",
    }}>
      <div style={{ flex: `${100 - whitePct}`, background: "#333" }} />
      <div style={{ flex: `${whitePct}`, background: "#eee" }} />
    </div>
  );
}
