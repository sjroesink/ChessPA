"use client";
import { Chessboard } from "react-chessboard";

interface Props {
  position: string;
  orientation?: "white" | "black";
  width?: number;
}

export default function ChessBoard({ position, orientation = "white", width = 400 }: Props) {
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
        }}
      />
    </div>
  );
}
