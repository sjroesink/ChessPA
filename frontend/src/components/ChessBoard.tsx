"use client";
import { Chessboard } from "react-chessboard";

interface Arrow {
  startSquare: string;
  endSquare: string;
  color?: string;
}

interface HighlightedSquare {
  square: string;
  color: string;
}

export interface SquareBadge {
  square: string;
  symbol: string;
  color: string; // background
  textColor?: string;
  title?: string;
}

interface Props {
  position: string;
  orientation?: "white" | "black";
  width?: number;
  arrows?: Arrow[];
  highlightedSquares?: HighlightedSquare[];
  badges?: SquareBadge[];
}

function squareToCoords(sq: string, orientation: "white" | "black"): { col: number; row: number } {
  const file = sq.charCodeAt(0) - "a".charCodeAt(0); // 0..7
  const rank = parseInt(sq[1], 10) - 1; // 0..7 (1=bottom)
  if (orientation === "white") {
    return { col: file, row: 7 - rank };
  }
  return { col: 7 - file, row: rank };
}

export default function ChessBoard({
  position,
  orientation = "white",
  width = 400,
  arrows,
  highlightedSquares,
  badges,
}: Props) {
  const squareStyles: Record<string, React.CSSProperties> = {};
  if (highlightedSquares) {
    for (const hs of highlightedSquares) {
      squareStyles[hs.square] = { backgroundColor: hs.color };
    }
  }

  const squareSize = width / 8;
  const badgeSize = Math.round(squareSize * 0.48);

  return (
    <div style={{ width: `${width}px`, height: `${width}px`, position: "relative" }}>
      <Chessboard
        options={{
          position,
          boardOrientation: orientation,
          allowDragging: false,
          boardStyle: { borderRadius: "0", width: "100%", height: "100%" },
          darkSquareStyle: { backgroundColor: "#779952" },
          lightSquareStyle: { backgroundColor: "#edeed1" },
          arrows: arrows && arrows.length > 0 ? arrows : undefined,
          squareStyles: Object.keys(squareStyles).length > 0 ? squareStyles : undefined,
        }}
      />
      {badges?.map((b, i) => {
        const { col, row } = squareToCoords(b.square, orientation);
        const left = col * squareSize + squareSize - badgeSize * 0.55;
        const top = row * squareSize - badgeSize * 0.2;
        return (
          <div
            key={`${b.square}-${i}`}
            title={b.title}
            style={{
              position: "absolute",
              left,
              top,
              width: badgeSize,
              height: badgeSize,
              borderRadius: "50%",
              background: b.color,
              color: b.textColor ?? "#fff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 800,
              fontSize: `${Math.round(badgeSize * 0.55)}px`,
              lineHeight: 1,
              pointerEvents: "auto",
              boxShadow: "0 1px 3px rgba(0,0,0,0.35)",
              border: "2px solid #fff",
              zIndex: 10,
            }}
          >
            {b.symbol}
          </div>
        );
      })}
    </div>
  );
}
