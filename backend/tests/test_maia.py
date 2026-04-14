import chess
import pytest

from app.analysis.maia import (
    MAIA_RATINGS,
    maia_available,
    open_maia_engine,
    pick_maia_weight,
    predict_human_move,
)


def test_pick_weight_default_is_1500():
    weight, bucket = pick_maia_weight(None)
    assert bucket == 1500
    assert weight.name == "maia-1500.pb.gz"


@pytest.mark.parametrize(
    "rating,expected_bucket",
    [
        (800, 1100),
        (1199, 1100),
        (1200, 1100),  # equidistant from 1100 and 1300; min() picks first
        (1201, 1300),
        (1400, 1300),
        (1600, 1500),
        (1800, 1700),
        (2500, 1900),
    ],
)
def test_pick_weight_buckets_nearest(rating, expected_bucket):
    _, bucket = pick_maia_weight(rating)
    assert bucket == expected_bucket


def test_buckets_are_stable():
    assert MAIA_RATINGS == [1100, 1300, 1500, 1700, 1900]


@pytest.mark.skipif(not maia_available(), reason="Maia weights not installed")
def test_predict_returns_legal_move():
    eng = open_maia_engine(rating=1500)
    try:
        board = chess.Board()
        pred = predict_human_move(eng, board, rating=1500)
        legal_sans = [board.san(m) for m in board.legal_moves]
        assert pred.top1_san in legal_sans
        assert 0.0 <= pred.top1_prob <= 1.0
        assert pred.rating_used == 1500
        assert 1 <= len(pred.top_k) <= 5
    finally:
        eng.quit()
