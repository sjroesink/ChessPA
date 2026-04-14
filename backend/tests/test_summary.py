from app.analysis.summary import compute_game_summary, detect_phase


def test_detect_phase():
    assert detect_phase(1, 40) == "opening"
    assert detect_phase(10, 40) == "opening"
    assert detect_phase(11, 40) == "middlegame"
    assert detect_phase(30, 40) == "middlegame"
    assert detect_phase(35, 40) == "endgame"
    assert detect_phase(40, 40) == "endgame"


def test_compute_game_summary_legacy_shape_still_works():
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


def test_compute_game_summary_empty():
    summary = compute_game_summary([])
    assert summary["blunders"] == 0
    assert summary["avg_eval_loss"] == 0.0
    assert summary["accuracy_white"] is None
    assert summary["accuracy_black"] is None


def test_compute_game_summary_rich_fields():
    rows = [
        {
            "classification": "ok", "centipawn_loss": 0, "accuracy_percent": 100,
            "color": "white", "features": {"phase": "opening"}, "motifs": [],
            "move_number": 1, "total_moves": 20,
        },
        {
            "classification": "blunder", "centipawn_loss": 250, "accuracy_percent": 10,
            "color": "black", "features": {"phase": "middlegame"},
            "motifs": [{"type": "hanging"}, {"type": "fork"}],
            "move_number": 14, "total_moves": 20,
        },
        {
            "classification": "inaccuracy", "centipawn_loss": 50, "accuracy_percent": 70,
            "color": "white", "features": {"phase": "middlegame"},
            "motifs": [{"type": "fork"}],
            "move_number": 15, "total_moves": 20,
        },
    ]
    summary = compute_game_summary(rows, opening_moves_san=["e4", "e5", "Nf3", "Nc6", "Bb5"])
    assert summary["accuracy_white"] == 85  # (100 + 70) / 2
    assert summary["accuracy_black"] == 10
    assert "middlegame" in summary["phase_acpl"]
    assert summary["phase_acpl"]["middlegame"] == 150  # (250 + 50) / 2
    assert summary["motif_counts"] == {"hanging": 1, "fork": 2}
    assert summary["opening_eco"] is not None
    assert "Ruy Lopez" in summary["opening_name"] or "Spanish" in summary["opening_name"]
