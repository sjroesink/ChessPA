"""Per-move fact bundle: everything the CCC prompt needs, in one dict."""

from __future__ import annotations

import chess


def build_move_fact_bundle(move_row: dict, user_color: str, motifs: list[dict], features: dict) -> dict:
    """Collect FEN-derived context + move fields + motifs + features for prompting."""
    board = chess.Board(move_row["fen"])
    legal_sans = [board.san(m) for m in board.legal_moves]
    user_perspective = None
    if "color" in move_row and user_color in ("white", "black"):
        user_perspective = move_row["color"] == user_color

    return {
        "move_san": move_row["move_san"],
        "move_uci": move_row.get("move_uci"),
        "fen": move_row["fen"],
        "legal_moves": legal_sans,
        "classification": move_row["classification"],
        "best_move_san": move_row["best_move_san"],
        "eval_before_cp": move_row.get("eval_before"),
        "eval_after_cp": move_row.get("eval_after"),
        "centipawn_loss": move_row.get("centipawn_loss"),
        "win_percent_before": move_row.get("win_percent_before"),
        "win_percent_after": move_row.get("win_percent_after"),
        "accuracy_percent": move_row.get("accuracy_percent"),
        "is_critical_moment": bool(move_row.get("is_critical_moment")),
        "multipv": move_row.get("multipv") or [],
        "motifs": motifs or [],
        "features": features or {},
        "user_perspective": user_perspective,
        "maia": {
            "top1_san": move_row.get("maia_top1_san"),
            "top1_prob": move_row.get("maia_top1_prob"),
            "match_played": move_row.get("maia_match_played"),
            "rating_used": move_row.get("maia_rating_used"),
        },
    }
