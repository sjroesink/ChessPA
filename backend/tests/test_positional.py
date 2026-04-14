import chess

from app.analysis.positional import extract_features


def test_phase_opening_start():
    feats = extract_features(chess.Board())
    assert feats["phase"] == "opening"


def test_phase_endgame_low_material():
    board = chess.Board("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")
    feats = extract_features(board)
    assert feats["phase"] == "endgame"


def test_isolated_pawn_detected():
    board = chess.Board("4k3/8/8/8/8/8/3P4/4K3 w - - 0 1")
    feats = extract_features(board)
    assert feats["pawn_structure"]["white"]["isolated"] >= 1


def test_doubled_pawns_detected():
    board = chess.Board("4k3/8/8/8/3P4/3P4/8/4K3 w - - 0 1")
    feats = extract_features(board)
    assert feats["pawn_structure"]["white"]["doubled"] >= 1


def test_passed_pawn_detected():
    # Lone white pawn on d4, no black pawns ahead or adjacent → passed.
    board = chess.Board("4k3/8/8/8/3P4/8/8/4K3 w - - 0 1")
    feats = extract_features(board)
    assert feats["pawn_structure"]["white"]["passed"] == 1


def test_bishop_pair_detected():
    board = chess.Board("4k3/8/8/8/8/8/8/2B1KB2 w - - 0 1")
    feats = extract_features(board)
    assert feats["bishop_pair_white"] is True
    assert feats["bishop_pair_black"] is False


def test_king_safety_open_files_score():
    # Exposed king — no nearby pawn shelter → score low.
    exposed = extract_features(chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1"))
    castled = extract_features(chess.Board("rnbq1rk1/pppp1ppp/5n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 w - - 0 1"))
    assert exposed["king_safety"]["white"] < castled["king_safety"]["white"]
