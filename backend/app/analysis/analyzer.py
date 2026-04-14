"""Orchestrated per-move analysis: Stockfish MultiPV + optional Maia + Lichess win%/accuracy."""

import io

import chess
import chess.pgn

from app.analysis.scoring import (
    accuracy_from_win_delta,
    label_from_win_drop,
    win_percent_from_cp,
)
from app.analysis.stockfish import analyze_multipv
from app.config import settings


def analyze_game_moves(
    engine,
    pgn_text: str,
    maia_engine=None,
    maia_rating: int | None = None,
    depth: int | None = None,
    progress_cb=None,
) -> list[dict]:
    """Produce a rich per-move fact dict for every ply of the game.

    `progress_cb(ply_index, total_plies, move_number, color, move_san)` is invoked
    before each ply's Stockfish call so callers can surface live progress.
    """
    if depth is None:
        depth = settings.stockfish_depth
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return []

    board = game.board()
    moves = list(game.mainline_moves())
    total_plies = len(moves)
    total_moves = (total_plies + 1) // 2
    results: list[dict] = []

    for i, move in enumerate(moves):
        move_number = (i // 2) + 1
        color = "white" if i % 2 == 0 else "black"
        fen_before = board.fen()

        upcoming_san = board.san(move)
        if progress_cb is not None:
            try:
                progress_cb(i, total_plies, move_number, color, upcoming_san)
            except Exception:
                pass

        before = analyze_multipv(engine, board, depth=depth, multipv=settings.multipv_count)
        if not before.multipv:
            board.push(move)
            continue

        move_san = upcoming_san
        move_uci = move.uci()
        eval_before = before.multipv[0].eval_cp
        best_san = before.multipv[0].san

        gap = 0.0
        if len(before.multipv) >= 2:
            gap = before.multipv[0].eval_cp - before.multipv[1].eval_cp
        is_critical = gap >= settings.critical_moment_cp_gap

        maia_top1 = maia_prob = maia_match = maia_rating_used = None
        if maia_engine is not None:
            try:
                from app.analysis.maia import predict_human_move

                pred = predict_human_move(maia_engine, board, rating=maia_rating)
                maia_top1 = pred.top1_san
                maia_prob = pred.top1_prob
                maia_match = pred.top1_san == move_san
                maia_rating_used = pred.rating_used
            except Exception as exc:  # pragma: no cover - runtime resilience
                print(f"Maia predict failed at ply {i}: {exc}")

        board.push(move)
        after = analyze_multipv(engine, board, depth=depth, multipv=1)
        eval_after_stm = -after.multipv[0].eval_cp if after.multipv else eval_before
        board.pop()

        win_before = win_percent_from_cp(eval_before)
        win_after = win_percent_from_cp(eval_after_stm)
        win_drop = max(0.0, win_before - win_after)
        accuracy = accuracy_from_win_delta(win_drop)
        drop_label = label_from_win_drop(win_drop)
        classification = drop_label if drop_label is not None else ("best" if move_san == best_san else "ok")
        cpl = max(0.0, eval_before - eval_after_stm)

        results.append(
            {
                "move_number": move_number,
                "color": color,
                "move_san": move_san,
                "move_uci": move_uci,
                "fen": fen_before,
                "eval_before": eval_before,
                "eval_after": eval_after_stm,
                "centipawn_loss": cpl,
                "win_percent_before": win_before,
                "win_percent_after": win_after,
                "accuracy_percent": accuracy,
                "classification": classification,
                "best_move_san": best_san,
                "total_moves": total_moves,
                "is_critical_moment": is_critical,
                "multipv": [
                    {
                        "rank": pv.rank,
                        "san": pv.san,
                        "uci": pv.uci,
                        "eval_cp": pv.eval_cp,
                        "pv_san": pv.pv_san,
                    }
                    for pv in before.multipv
                ],
                "maia_top1_san": maia_top1,
                "maia_top1_prob": maia_prob,
                "maia_match_played": maia_match,
                "maia_rating_used": maia_rating_used,
            }
        )
        board.push(move)

    return results
