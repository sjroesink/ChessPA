"""Positional-feature extraction from a single FEN.

Signals exposed per board:
  - phase: opening / middlegame / endgame
  - pawn_structure per side: isolated, doubled, backward, passed counts
  - king_safety per side: 0.0 (fully open) — 1.0 (safe)
  - bishop_pair per side: bool
"""

from __future__ import annotations

import chess


def extract_features(board: chess.Board) -> dict:
    return {
        "phase": _game_phase(board),
        "pawn_structure": {
            "white": _pawn_structure(board, chess.WHITE),
            "black": _pawn_structure(board, chess.BLACK),
        },
        "king_safety": {
            "white": _king_safety(board, chess.WHITE),
            "black": _king_safety(board, chess.BLACK),
        },
        "bishop_pair_white": _has_bishop_pair(board, chess.WHITE),
        "bishop_pair_black": _has_bishop_pair(board, chess.BLACK),
    }


def _game_phase(board: chess.Board) -> str:
    non_pawn_non_king = sum(
        1 for p in board.piece_map().values() if p.piece_type not in (chess.KING, chess.PAWN)
    )
    if non_pawn_non_king <= 6:
        return "endgame"
    if board.fullmove_number <= 12:
        return "opening"
    return "middlegame"


def _pawn_files(board: chess.Board, color: chess.Color) -> list[int]:
    return [
        chess.square_file(sq)
        for sq, p in board.piece_map().items()
        if p.piece_type == chess.PAWN and p.color == color
    ]


def _pawn_structure(board: chess.Board, color: chess.Color) -> dict:
    files = _pawn_files(board, color)
    file_counts = [files.count(f) for f in range(8)]
    doubled = sum(max(0, c - 1) for c in file_counts)
    isolated = 0
    for f in range(8):
        if file_counts[f] == 0:
            continue
        left = file_counts[f - 1] if f > 0 else 0
        right = file_counts[f + 1] if f < 7 else 0
        if left == 0 and right == 0:
            isolated += file_counts[f]
    passed = _count_passed(board, color)
    # Backward: has no same-colour pawn on adjacent files behind it AND front square is controlled by an enemy pawn.
    backward = _count_backward(board, color)
    return {"isolated": isolated, "doubled": doubled, "backward": backward, "passed": passed}


def _count_passed(board: chess.Board, color: chess.Color) -> int:
    enemy = not color
    count = 0
    for sq, p in board.piece_map().items():
        if p.piece_type != chess.PAWN or p.color != color:
            continue
        file_ = chess.square_file(sq)
        rank = chess.square_rank(sq)
        blocked = False
        for enemy_sq, ep in board.piece_map().items():
            if ep.piece_type != chess.PAWN or ep.color != enemy:
                continue
            ef = chess.square_file(enemy_sq)
            er = chess.square_rank(enemy_sq)
            if abs(ef - file_) <= 1:
                if (color == chess.WHITE and er > rank) or (color == chess.BLACK and er < rank):
                    blocked = True
                    break
        if not blocked:
            count += 1
    return count


def _count_backward(board: chess.Board, color: chess.Color) -> int:
    count = 0
    for sq, p in board.piece_map().items():
        if p.piece_type != chess.PAWN or p.color != color:
            continue
        file_ = chess.square_file(sq)
        rank = chess.square_rank(sq)
        # Check for same-colour pawn on adjacent file at same or earlier rank (our "support").
        has_support = False
        for friend_sq, fp in board.piece_map().items():
            if fp.piece_type != chess.PAWN or fp.color != color or friend_sq == sq:
                continue
            ff = chess.square_file(friend_sq)
            fr = chess.square_rank(friend_sq)
            if abs(ff - file_) == 1:
                if (color == chess.WHITE and fr <= rank) or (color == chess.BLACK and fr >= rank):
                    has_support = True
                    break
        if has_support:
            continue
        # Check if the square in front is attacked by an enemy pawn.
        forward_rank = rank + (1 if color == chess.WHITE else -1)
        if not 0 <= forward_rank <= 7:
            continue
        front_sq = chess.square(file_, forward_rank)
        enemy_pawn_attacks = board.attackers(not color, front_sq)
        if any(board.piece_at(a).piece_type == chess.PAWN for a in enemy_pawn_attacks):
            count += 1
    return count


def _king_safety(board: chess.Board, color: chess.Color) -> float:
    king_sq = board.king(color)
    if king_sq is None:
        return 0.0
    king_file = chess.square_file(king_sq)
    open_files = 0
    for df in (-1, 0, 1):
        f = king_file + df
        if not 0 <= f <= 7:
            continue
        has_pawn = any(
            board.piece_at(chess.square(f, r)) == chess.Piece(chess.PAWN, color)
            for r in range(8)
        )
        if not has_pawn:
            open_files += 1
    return max(0.0, 1.0 - open_files / 3.0)


def _has_bishop_pair(board: chess.Board, color: chess.Color) -> bool:
    bishops = [
        p
        for p in board.piece_map().values()
        if p.piece_type == chess.BISHOP and p.color == color
    ]
    return len(bishops) >= 2
