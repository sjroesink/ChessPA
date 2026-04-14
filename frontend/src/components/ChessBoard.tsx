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

interface Props {
  position: string;
  orientation?: "white" | "black";
  width?: number;
  arrows?: Arrow[];
  highlightedSquares?: HighlightedSquare[];
}

export default function ChessBoard({
  position,
  orientation = "white",
  width = 400,
  arrows,
  highlightedSquares,
}: Props) {
  const squareStyles: Record<string, React.CSSProperties> = {};
  if (highlightedSquares) {
    for (const hs of highlightedSquares) {
      squareStyles[hs.square] = { backgroundColor: hs.color };
    }
  }

  return (
    <div style={{ width: `${width}px`, height: `${width}px` }}>
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
    </div>
  );
}
