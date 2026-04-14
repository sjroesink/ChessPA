import io
import chess
import chess.pgn
from app.analysis.stockfish import analyze_position, MoveEval
from app.analysis.classifier import classify_move


def analyze_game_moves(engine, pgn_text: str, depth: int = 20) -> list[dict]:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return []

    board = game.board()
    moves = list(game.mainline_moves())
    total_moves = (len(moves) + 1) // 2
    results = []

    for i, move in enumerate(moves):
        move_number = (i // 2) + 1
        color = "white" if i % 2 == 0 else "black"

        eval_result: MoveEval = analyze_position(engine, board, move, depth)
        classification = classify_move(eval_result.centipawn_loss)

        results.append({
            "move_number": move_number,
            "color": color,
            "move_san": eval_result.move_san,
            "eval_before": eval_result.eval_before,
            "eval_after": eval_result.eval_after,
            "best_move_san": eval_result.best_move_san,
            "classification": classification,
            "centipawn_loss": eval_result.centipawn_loss,
            "total_moves": total_moves,
        })
        board.push(move)

    return results
