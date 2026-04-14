import shutil

import chess
import pytest

from app.analysis.maia import (
    maia_available,
    open_maia_engine,
    pick_maia_weight,
    predict_human_move,
    _discover_ratings,
)


def test_discover_ratings_returns_sorted_list():
    r = _discover_ratings()
    assert isinstance(r, list)
    assert len(r) >= 1
    assert r == sorted(r)


def test_pick_weight_returns_existing_bucket():
    weight, bucket = pick_maia_weight(1700)
    assert bucket in _discover_ratings()
    assert weight.name == f"maia-{bucket}.pb.gz"


def test_pick_weight_nearest_bucket():
    ratings = _discover_ratings()
    if not ratings:
        pytest.skip("no weights to test bucketing")
    target = ratings[0] - 200
    _, bucket = pick_maia_weight(target)
    # Should pick the lowest available bucket (closest to below-range target).
    assert bucket == ratings[0]


def test_pick_weight_default_when_none():
    _, bucket = pick_maia_weight(None)
    assert bucket in _discover_ratings()


@pytest.mark.skipif(
    not maia_available() or shutil.which("lc0") is None,
    reason="Maia weights or lc0 binary not installed",
)
def test_predict_returns_legal_move():
    eng = open_maia_engine(rating=1700)
    try:
        board = chess.Board()
        pred = predict_human_move(eng, board, rating=1700)
        legal_sans = [board.san(m) for m in board.legal_moves]
        assert pred.top1_san in legal_sans
        assert 0.0 <= pred.top1_prob <= 1.0
        assert 1 <= len(pred.top_k) <= 5
    finally:
        eng.quit()
