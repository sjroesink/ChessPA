import shutil
import chess
import pytest

from app.analysis.stockfish import analyze_multipv, open_engine

pytestmark = pytest.mark.skipif(shutil.which("stockfish") is None, reason="Stockfish binary not installed")


@pytest.fixture(scope="module")
def engine():
    eng = open_engine()
    yield eng
    eng.quit()


def test_multipv_returns_requested_count(engine):
    board = chess.Board()
    result = analyze_multipv(engine, board, depth=8, multipv=3)
    assert len(result.multipv) == 3
    assert result.multipv[0].rank == 1
    assert all(pv.san for pv in result.multipv)
    assert result.turn == "white"


def test_multipv_eval_descending(engine):
    board = chess.Board()
    result = analyze_multipv(engine, board, depth=8, multipv=3)
    evals = [pv.eval_cp for pv in result.multipv]
    assert evals[0] >= evals[1] >= evals[2]


def test_multipv_pv_san_non_empty(engine):
    board = chess.Board()
    result = analyze_multipv(engine, board, depth=8, multipv=2)
    for pv in result.multipv:
        assert len(pv.pv_san) >= 1
