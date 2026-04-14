from unittest.mock import MagicMock, patch

from app.analysis.analyzer import analyze_game_moves
from app.analysis.stockfish import MultiPVResult, PVLine

SAMPLE_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0"


def _mpv(san: str, eval_cp: float, rank: int = 1) -> MultiPVResult:
    return MultiPVResult(
        fen="",
        turn="white",
        multipv=[
            PVLine(rank=rank, san=san, uci="e2e4", eval_cp=eval_cp, pv_san=[san]),
            PVLine(rank=rank + 1, san="d4", uci="d2d4", eval_cp=eval_cp - 20, pv_san=["d4"]),
            PVLine(rank=rank + 2, san="c4", uci="c2c4", eval_cp=eval_cp - 40, pv_san=["c4"]),
        ],
    )


def test_analyze_game_moves_rich_shape():
    # For 6 plies, analyzer calls analyze_multipv 12 times (before + after each move).
    # Alternate "before" and "after" responses.
    multipv_sequence = []
    for i in range(6):
        multipv_sequence.append(_mpv("best", 20.0))  # before
        multipv_sequence.append(_mpv("best", -15.0))  # after, from opponent STM
    with patch("app.analysis.analyzer.analyze_multipv") as mock_mpv:
        mock_mpv.side_effect = multipv_sequence
        engine = MagicMock()
        results = analyze_game_moves(engine, SAMPLE_PGN, depth=8)

    assert len(results) == 6
    first = results[0]
    for key in (
        "move_number",
        "color",
        "move_san",
        "fen",
        "eval_before",
        "eval_after",
        "centipawn_loss",
        "win_percent_before",
        "win_percent_after",
        "accuracy_percent",
        "classification",
        "best_move_san",
        "is_critical_moment",
        "multipv",
    ):
        assert key in first
    assert len(first["multipv"]) == 3
    assert first["multipv"][0]["rank"] == 1
    assert first["color"] == "white"
    assert results[1]["color"] == "black"
    assert 0 <= first["accuracy_percent"] <= 100
    assert first["maia_top1_san"] is None  # no maia engine passed


def test_analyze_flags_critical_moment_on_wide_gap():
    # Make PV1 300cp better than PV2 → is_critical should be True
    multipv_sequence = []
    for _ in range(6):
        multipv_sequence.append(
            MultiPVResult(
                fen="",
                turn="white",
                multipv=[
                    PVLine(rank=1, san="best", uci="e2e4", eval_cp=500, pv_san=["best"]),
                    PVLine(rank=2, san="alt", uci="d2d4", eval_cp=100, pv_san=["alt"]),
                ],
            )
        )
        multipv_sequence.append(_mpv("after", -100))
    with patch("app.analysis.analyzer.analyze_multipv") as mock_mpv:
        mock_mpv.side_effect = multipv_sequence
        engine = MagicMock()
        results = analyze_game_moves(engine, SAMPLE_PGN, depth=8)
    assert results[0]["is_critical_moment"] is True
