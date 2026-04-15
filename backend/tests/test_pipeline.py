"""Schedule/priority tests for AnalysisSession — run without Stockfish."""

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.analysis.pipeline import AnalysisSession
from app.analysis.stages import ALL_STAGES


SAMPLE_PGN = (
    '[Event "?"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 1-0'
)


def _make_session(completed_stages_per_ply: list[list[str] | None]) -> AnalysisSession:
    @dataclass
    class StubRow:
        move_number: int
        color: str
        completed_stages: list[str] | None

    game = SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111",
        pgn=SAMPLE_PGN,
        user_color="white",
    )

    session = AnalysisSession(db=None, game=game)  # type: ignore[arg-type]

    # Manually populate loaded state (avoid DB round-trip).
    session._loaded = True
    import chess
    import chess.pgn
    import io

    pgn_game = chess.pgn.read_game(io.StringIO(SAMPLE_PGN))
    board = pgn_game.board()
    for i, move in enumerate(pgn_game.mainline_moves()):
        move_number = (i // 2) + 1
        color = "white" if i % 2 == 0 else "black"
        session._plies.append(
            SimpleNamespace(
                ply=i,
                move_number=move_number,
                color=color,
                move_san=board.san(move),
                move_uci=move.uci(),
                fen_before=board.fen(),
                played_move=move,
                board_before=board.copy(stack=False),
            )  # type: ignore[arg-type]
        )
        if i < len(completed_stages_per_ply):
            stages = completed_stages_per_ply[i]
            session._rows[i] = StubRow(move_number=move_number, color=color, completed_stages=stages)  # type: ignore[assignment]
        board.push(move)
    return session


def test_queue_empty_when_all_stages_complete():
    session = _make_session([list(ALL_STAGES)] * 10)
    session._rebuild_queue()
    assert session._pop_next() is None


def test_queue_fills_missing_stages_in_priority_order():
    # all plies missing everything
    session = _make_session([None] * 10)
    session._rebuild_queue()
    picks: list[tuple[int, str]] = []
    while True:
        entry = session._pop_next()
        if entry is None:
            break
        picks.append((entry.ply, entry.stage))
    # No focus, no deep_all → only shallow + standard pulled; deep/enrich skipped
    assert all(stage in ("shallow", "standard") for _, stage in picks)
    # All 10 plies covered for each of the two stages
    shallows = [p for p, s in picks if s == "shallow"]
    standards = [p for p, s in picks if s == "standard"]
    assert sorted(shallows) == list(range(10))
    assert sorted(standards) == list(range(10))
    # Shallows must come before any standards (lower priority number = earlier)
    shallow_positions = [idx for idx, (_, s) in enumerate(picks) if s == "shallow"]
    standard_positions = [idx for idx, (_, s) in enumerate(picks) if s == "standard"]
    assert max(shallow_positions) < min(standard_positions)


def test_focus_puts_focused_ply_first():
    session = _make_session([None] * 10)
    session.set_focus(5)
    session._rebuild_queue()
    first = session._pop_next()
    assert first.ply == 5
    assert first.stage in ("deep", "shallow")  # focus-deep ties with focus-shallow in priority


def test_deep_all_schedules_deep_and_enrich_for_all():
    session = _make_session([list(ALL_STAGES[:2])] * 10)  # shallow+standard done on every ply
    session.set_deep_all(True)
    picks: list[tuple[int, str]] = []
    while True:
        entry = session._pop_next()
        if entry is None:
            break
        picks.append((entry.ply, entry.stage))
    assert all(stage in ("deep", "enrich") for _, stage in picks), picks
    assert {p for p, s in picks if s == "deep"} == set(range(10))
    assert {p for p, s in picks if s == "enrich"} == set(range(10))


def test_focus_change_cancels_current():
    session = _make_session([None] * 5)
    assert session._cancel_current.is_set() is False
    session.set_focus(2)
    assert session._cancel_current.is_set() is True
