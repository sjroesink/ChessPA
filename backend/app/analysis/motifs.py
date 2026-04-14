"""Tactical motif detector.

Two-phase design:
  1. `detect_geometric_motifs` — fast bitboard/attack-graph scan (false positives allowed).
  2. `verify_motifs`           — drop candidates whose Stockfish eval does not actually
                                 favour the side to move by >= gain_threshold_cp.

Motifs returned:
  - fork            (one attacker threatens two+ pieces of equal-or-higher value)
  - absolute_pin    (slider pins a piece against its king)
  - relative_pin    (slider pins a piece against a more-valuable piece)
  - skewer          (more-valuable piece is in front; moves, exposing a cheaper one)
  - hanging         (undefended enemy piece under attack)

`discovered_attack` is deferred — full detection needs move-generation context
that the current single-FEN API does not supply.
"""

from __future__ import annotations

import chess

PIECE_VALUE = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 100,
}


def _sq(square: int) -> str:
    return chess.square_name(square)


def detect_geometric_motifs(board: chess.Board, last_move_uci: str | None = None) -> list[dict]:
    """Return candidate motifs from the STM's point of view.

    `last_move_uci` is accepted for API symmetry with future discovered-attack
    detection but currently unused.
    """
    motifs: list[dict] = []
    motifs.extend(_find_forks(board))
    motifs.extend(_find_pins_and_skewers(board))
    motifs.extend(_find_hanging_pieces(board))
    return motifs


def _find_forks(board: chess.Board) -> list[dict]:
    out: list[dict] = []
    attacker_color = board.turn
    for sq, piece in board.piece_map().items():
        if piece.color != attacker_color:
            continue
        attacks = board.attacks(sq)
        targets: list[int] = []
        for t_sq in attacks:
            tgt = board.piece_at(t_sq)
            if (
                tgt is not None
                and tgt.color != piece.color
                and PIECE_VALUE[tgt.piece_type] >= PIECE_VALUE[piece.piece_type]
            ):
                targets.append(t_sq)
        if len(targets) >= 2:
            out.append(
                {
                    "type": "fork",
                    "attacker": _sq(sq),
                    "squares": [_sq(t) for t in targets],
                }
            )
    return out


def _ray_squares(from_sq: int, direction: tuple[int, int]) -> list[int]:
    df, dr = direction
    file_ = chess.square_file(from_sq) + df
    rank = chess.square_rank(from_sq) + dr
    out: list[int] = []
    while 0 <= file_ <= 7 and 0 <= rank <= 7:
        out.append(chess.square(file_, rank))
        file_ += df
        rank += dr
    return out


_SLIDER_DIRECTIONS: dict[chess.PieceType, list[tuple[int, int]]] = {
    chess.BISHOP: [(1, 1), (1, -1), (-1, 1), (-1, -1)],
    chess.ROOK: [(1, 0), (-1, 0), (0, 1), (0, -1)],
    chess.QUEEN: [(1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1)],
}


def _find_pins_and_skewers(board: chess.Board) -> list[dict]:
    out: list[dict] = []
    for sq, piece in board.piece_map().items():
        if piece.piece_type not in _SLIDER_DIRECTIONS:
            continue
        for direction in _SLIDER_DIRECTIONS[piece.piece_type]:
            first = second = None
            for ray_sq in _ray_squares(sq, direction):
                p = board.piece_at(ray_sq)
                if p is None:
                    continue
                if first is None:
                    first = (ray_sq, p)
                else:
                    second = (ray_sq, p)
                    break
            if first is None or second is None:
                continue
            first_sq, first_piece = first
            second_sq, second_piece = second
            # Both targets must be enemy relative to slider
            if first_piece.color == piece.color or second_piece.color == piece.color:
                continue
            if second_piece.piece_type == chess.KING:
                out.append(
                    {
                        "type": "absolute_pin",
                        "attacker": _sq(sq),
                        "pinned": _sq(first_sq),
                        "target": _sq(second_sq),
                    }
                )
            elif PIECE_VALUE[second_piece.piece_type] > PIECE_VALUE[first_piece.piece_type]:
                out.append(
                    {
                        "type": "relative_pin",
                        "attacker": _sq(sq),
                        "pinned": _sq(first_sq),
                        "target": _sq(second_sq),
                    }
                )
            elif PIECE_VALUE[first_piece.piece_type] > PIECE_VALUE[second_piece.piece_type]:
                out.append(
                    {
                        "type": "skewer",
                        "attacker": _sq(sq),
                        "front": _sq(first_sq),
                        "back": _sq(second_sq),
                    }
                )
    return out


def _find_hanging_pieces(board: chess.Board) -> list[dict]:
    out: list[dict] = []
    attacker_color = board.turn
    for sq, piece in board.piece_map().items():
        if piece.color == attacker_color or piece.piece_type == chess.KING:
            continue
        attackers = board.attackers(attacker_color, sq)
        if not attackers:
            continue
        defenders = board.attackers(not attacker_color, sq)
        if defenders:
            continue
        out.append(
            {
                "type": "hanging",
                "square": _sq(sq),
                "attackers": [_sq(a) for a in attackers],
            }
        )
    return out


def verify_motifs(
    engine,
    board: chess.Board,
    motifs: list[dict],
    depth: int = 12,
    gain_threshold_cp: float = 150.0,
) -> list[dict]:
    """Drop motifs where the engine does not show a clear material/positional edge for STM."""
    if not motifs:
        return []
    from app.analysis.stockfish import analyze_multipv

    baseline = analyze_multipv(engine, board, depth=depth, multipv=1)
    if not baseline.multipv:
        return []
    base_cp = baseline.multipv[0].eval_cp
    if base_cp < gain_threshold_cp:
        return []
    return [{**m, "verified_gain_cp": base_cp} for m in motifs]
