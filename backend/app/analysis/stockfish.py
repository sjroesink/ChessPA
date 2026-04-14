import chess
import chess.engine
from dataclasses import dataclass


@dataclass
class MoveEval:
    move_san: str
    eval_before: float
    eval_after: float
    best_move_san: str
    centipawn_loss: float


def analyze_position(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    move: chess.Move,
    depth: int = 20,
) -> MoveEval:
    """Analyze a single move: get eval before, eval after, and best move."""
    info_before = engine.analyse(board, chess.engine.Limit(depth=depth))
    eval_before = _score_to_cp(info_before["score"], board.turn)

    best_move = info_before.get("pv", [None])[0]
    best_move_san = board.san(best_move) if best_move else board.san(move)

    move_san = board.san(move)
    board.push(move)
    info_after = engine.analyse(board, chess.engine.Limit(depth=depth))
    eval_after = _score_to_cp(info_after["score"], board.turn)
    board.pop()

    # Centipawn loss calculation
    # eval_before: from side-to-move perspective
    # eval_after: from opponent's perspective (after the move)
    # Loss = what we had - what we have now
    # Convert both to White's perspective first
    if board.turn == chess.WHITE:
        cp_before = eval_before
        cp_after = -eval_after
    else:
        cp_before = -eval_before
        cp_after = eval_after

    centipawn_loss = max(0, cp_before - cp_after) if board.turn == chess.WHITE else max(0, cp_after - cp_before)

    return MoveEval(
        move_san=move_san,
        eval_before=cp_before,
        eval_after=cp_after,
        best_move_san=best_move_san,
        centipawn_loss=centipawn_loss,
    )


def _score_to_cp(score: chess.engine.PovScore, turn: chess.Color) -> float:
    relative = score.relative
    if relative.is_mate():
        mate_in = relative.mate()
        return 10000 if mate_in > 0 else -10000
    return float(relative.score(mate_score=10000))


def open_engine(path: str | None = None, threads: int | None = None, hash_mb: int | None = None) -> chess.engine.SimpleEngine:
    from app.config import settings
    engine = chess.engine.SimpleEngine.popen_uci(path or settings.stockfish_path)
    engine.configure({
        "Threads": threads or settings.stockfish_threads,
        "Hash": hash_mb or settings.stockfish_hash_mb,
    })
    return engine
