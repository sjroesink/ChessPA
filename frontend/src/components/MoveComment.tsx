"use client";
import PieceIcon, { pieceFromSan, stripSanPiece } from "@/components/PieceIcon";

// Match SAN moves: piece + optional disambiguation + capture + dest + promotion + check
// Also matches castling (O-O, O-O-O)
const SAN_REGEX = /\b([KQRBN][a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?|O-O-O|O-O|[a-h]x[a-h][1-8](?:=[QRBN])?[+#]?|[a-h][1-8])\b/g;

interface Props {
  text: string;
  color: "white" | "black";
}

/**
 * Render commentary text with embedded move references highlighted.
 * Each SAN move gets a piece icon (except pawns) and hover tooltip.
 */
export default function MoveComment({ text, color }: Props) {
  const parts: Array<{ text: string; isMove: boolean }> = [];
  let lastIdx = 0;

  for (const match of text.matchAll(SAN_REGEX)) {
    const idx = match.index ?? 0;
    if (idx > lastIdx) {
      parts.push({ text: text.slice(lastIdx, idx), isMove: false });
    }
    parts.push({ text: match[0], isMove: true });
    lastIdx = idx + match[0].length;
  }
  if (lastIdx < text.length) {
    parts.push({ text: text.slice(lastIdx), isMove: false });
  }

  return (
    <p style={{ fontSize: "13px", lineHeight: 1.5, margin: 0 }}>
      {parts.map((p, i) =>
        p.isMove ? (
          <span
            key={i}
            title={p.text}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "2px",
              padding: "0 4px",
              background: "var(--bg)",
              border: "1px solid var(--border)",
              borderRadius: 0,
              fontFamily: "monospace",
              fontWeight: 600,
              cursor: "help",
            }}
          >
            <PieceIcon piece={pieceFromSan(p.text)} color={color} size={13} />
            {stripSanPiece(p.text)}
          </span>
        ) : (
          <span key={i}>{p.text}</span>
        )
      )}
    </p>
  );
}
