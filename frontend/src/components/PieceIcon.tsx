"use client";
import Icon from "@mdi/react";
import {
  mdiChessKing,
  mdiChessQueen,
  mdiChessRook,
  mdiChessBishop,
  mdiChessKnight,
  mdiChessPawn,
} from "@mdi/js";

const PIECE_PATH: Record<string, string> = {
  K: mdiChessKing,
  Q: mdiChessQueen,
  R: mdiChessRook,
  B: mdiChessBishop,
  N: mdiChessKnight,
  P: mdiChessPawn,
};

interface Props {
  piece: "K" | "Q" | "R" | "B" | "N" | "P";
  color?: "white" | "black";
  size?: number;
}

export default function PieceIcon({ piece, color = "white", size = 16 }: Props) {
  if (piece === "P") return null;
  const path = PIECE_PATH[piece];
  if (!path) return null;
  const fill = color === "white" ? "#f5f5f5" : "#1a1a1a";
  const stroke = color === "white" ? "#1a1a1a" : "#f5f5f5";
  return (
    <span style={{ display: "inline-flex", verticalAlign: "middle" }}>
      <Icon
        path={path}
        size={`${size}px`}
        style={{
          fill,
          stroke,
          strokeWidth: 0.5,
          paintOrder: "stroke fill",
        }}
      />
    </span>
  );
}

/**
 * Parse a SAN move and return the piece letter.
 * Defaults to "P" for pawn moves (no leading piece letter).
 */
export function pieceFromSan(san: string): "K" | "Q" | "R" | "B" | "N" | "P" {
  const first = san[0];
  if (first === "O") return "K"; // castling
  if (["K", "Q", "R", "B", "N"].includes(first)) {
    return first as "K" | "Q" | "R" | "B" | "N";
  }
  return "P";
}

/**
 * Strip the leading piece letter from SAN (so the icon replaces it).
 * e.g. "Nxf3" → "xf3", "e4" → "e4", "O-O" → "O-O"
 */
export function stripSanPiece(san: string): string {
  if (san.startsWith("O-")) return san; // castling
  const first = san[0];
  if (["K", "Q", "R", "B", "N"].includes(first)) {
    return san.slice(1);
  }
  return san;
}
