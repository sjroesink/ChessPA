from app.analysis.summary import compute_game_summary, detect_phase

def test_detect_phase():
    assert detect_phase(1, 40) == "opening"
    assert detect_phase(10, 40) == "opening"
    assert detect_phase(11, 40) == "middlegame"
    assert detect_phase(30, 40) == "middlegame"
    assert detect_phase(35, 40) == "endgame"
    assert detect_phase(40, 40) == "endgame"

def test_compute_game_summary():
    move_analyses = [
        {"classification": "best", "eval_loss": 2, "move_number": 1, "total_moves": 30},
        {"classification": "good", "eval_loss": 15, "move_number": 5, "total_moves": 30},
        {"classification": "blunder", "eval_loss": 150, "move_number": 15, "total_moves": 30},
        {"classification": "mistake", "eval_loss": 80, "move_number": 20, "total_moves": 30},
        {"classification": "inaccuracy", "eval_loss": 40, "move_number": 28, "total_moves": 30},
    ]
    summary = compute_game_summary(move_analyses)
    assert summary["blunders"] == 1
    assert summary["mistakes"] == 1
    assert summary["inaccuracies"] == 1
    assert summary["avg_eval_loss"] > 0
    assert "opening" in summary["phase_scores"]
    assert "middlegame" in summary["phase_scores"]
    assert "endgame" in summary["phase_scores"]

def test_compute_game_summary_empty():
    summary = compute_game_summary([])
    assert summary["blunders"] == 0
    assert summary["avg_eval_loss"] == 0.0
