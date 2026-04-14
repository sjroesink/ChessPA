import shutil
import chess
import pytest

from app.analysis.motifs import detect_geometric_motifs, verify_motifs


def test_knight_fork_queen_rook():
    # White Nd5 forks black queen c7 and black rook e7 (legal, no king on attacked squares).
    board = chess.Board("4k3/2q1r3/8/3N4/8/8/8/6K1 w - - 0 1")
    motifs = detect_geometric_motifs(board)
    forks = [m for m in motifs if m["type"] == "fork"]
    assert any(f["attacker"] == "d5" for f in forks)


def test_absolute_pin_rook_on_king_file():
    # Black king e8, black bishop e4, white rook e1 → absolute pin of bishop on king.
    board = chess.Board("4k3/8/8/8/4b3/8/8/4R1K1 w - - 0 1")
    motifs = detect_geometric_motifs(board)
    assert any(m["type"] == "absolute_pin" and m["pinned"] == "e4" for m in motifs)


def test_skewer_front_queen_back_rook():
    # White rook d1 attacks black queen d3 with black rook d5 behind it on the d-file.
    board = chess.Board("4k3/8/8/3r4/8/3q4/8/3R2K1 w - - 0 1")
    motifs = detect_geometric_motifs(board)
    assert any(m["type"] == "skewer" and m["front"] == "d3" and m["back"] == "d5" for m in motifs)


def test_hanging_piece_undefended_bishop():
    # White bishop g3 attacks undefended black bishop on d6 (diagonal).
    board = chess.Board("4k3/8/3b4/8/8/6B1/8/6K1 w - - 0 1")
    motifs = detect_geometric_motifs(board)
    hangs = [m for m in motifs if m["type"] == "hanging"]
    assert any(h["square"] == "d6" for h in hangs)


def test_starting_position_has_no_tactics():
    motifs = detect_geometric_motifs(chess.Board())
    assert not any(m["type"] in ("fork", "absolute_pin", "skewer", "hanging") for m in motifs)


@pytest.mark.skipif(shutil.which("stockfish") is None, reason="Stockfish binary not installed")
def test_verify_drops_false_positives():
    from app.analysis.stockfish import open_engine

    eng = open_engine()
    try:
        # Starting position — any fake motif should be rejected (eval ~0)
        fake = [{"type": "fork", "attacker": "e2", "squares": ["e4", "d4"]}]
        verified = verify_motifs(eng, chess.Board(), fake, depth=8)
        assert verified == []
    finally:
        eng.quit()
