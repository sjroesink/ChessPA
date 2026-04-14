from unittest.mock import MagicMock, patch
from app.analysis.analyzer import analyze_game_moves
from app.analysis.stockfish import MoveEval

SAMPLE_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0"

def test_analyze_game_moves():
    mock_evals = [
        MoveEval("e4", 0, 20, "e4", 0),
        MoveEval("e5", 20, 15, "e5", 5),
        MoveEval("Nf3", 15, 30, "Nf3", 0),
        MoveEval("Nc6", 30, 25, "Nc6", 5),
        MoveEval("Bb5", 25, 60, "Bb5", 0),
        MoveEval("a6", 60, 45, "a6", 15),
    ]

    with patch("app.analysis.analyzer.analyze_position") as mock_analyze:
        mock_analyze.side_effect = mock_evals
        mock_engine = MagicMock()
        results = analyze_game_moves(mock_engine, SAMPLE_PGN, depth=20)

    assert len(results) == 6
    assert results[0]["move_san"] == "e4"
    assert results[0]["move_number"] == 1
    assert results[0]["color"] == "white"
    assert results[1]["color"] == "black"
    assert results[5]["move_number"] == 3
    assert "classification" in results[0]
