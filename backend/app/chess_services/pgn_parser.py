import hashlib
import io
from datetime import datetime, timezone

import chess.pgn


def parse_pgn(pgn_text: str) -> dict:
    """Parse a PGN string and extract game metadata."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("Invalid PGN")

    headers = game.headers
    moves = list(game.mainline_moves())

    date_str = headers.get("Date", "????.??.??")
    played_at = None
    try:
        played_at = datetime.strptime(date_str, "%Y.%m.%d").replace(tzinfo=timezone.utc)
    except ValueError:
        played_at = datetime.now(timezone.utc)

    white_elo = _safe_int(headers.get("WhiteElo"))
    black_elo = _safe_int(headers.get("BlackElo"))

    # move_count = number of full moves (rounded up) + 1
    # e.g. 10 plies (5 full moves) → 6, 2 plies (1 full move) → 2
    num_plies = len(moves)
    move_count = (num_plies + 1) // 2 + 1

    return {
        "pgn": pgn_text.strip(),
        "white_username": headers.get("White", "?"),
        "black_username": headers.get("Black", "?"),
        "result_raw": headers.get("Result", "*"),
        "white_elo": white_elo,
        "black_elo": black_elo,
        "time_control": headers.get("TimeControl"),
        "opening_eco": headers.get("ECO"),
        "opening_name": headers.get("Opening"),
        "played_at": played_at,
        "move_count": move_count,
    }


def determine_result(result_raw: str, is_white: bool) -> str:
    """Determine win/loss/draw from the perspective of the given player.

    Args:
        result_raw: PGN result string ("1-0", "0-1", "1/2-1/2", "*")
        is_white: True if the result should be from white's perspective,
                  False for black's perspective.

    Returns:
        "win", "loss", or "draw"
    """
    if result_raw == "1/2-1/2":
        return "draw"
    white_won = result_raw == "1-0"
    if is_white:
        return "win" if white_won else "loss"
    else:
        return "loss" if white_won else "win"


def compute_content_hash(moves_text: str, date: str, white: str, black: str) -> str:
    """Compute SHA256 hash for game deduplication."""
    content = f"{moves_text}|{date}|{white}|{black}"
    return hashlib.sha256(content.encode()).hexdigest()


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
