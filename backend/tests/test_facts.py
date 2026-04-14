from app.analysis.facts import build_move_fact_bundle


BASE_MOVE = {
    "move_san": "e4",
    "move_uci": "e2e4",
    "color": "white",
    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "eval_before": 20.0,
    "eval_after": 15.0,
    "centipawn_loss": 5.0,
    "win_percent_before": 55.0,
    "win_percent_after": 53.0,
    "accuracy_percent": 95.0,
    "classification": "best",
    "best_move_san": "e4",
    "is_critical_moment": False,
    "multipv": [{"rank": 1, "san": "e4", "pv_san": ["e4"], "eval_cp": 20}],
    "maia_top1_san": "e4",
    "maia_top1_prob": 0.3,
    "maia_match_played": True,
    "maia_rating_used": 1500,
}


def test_bundle_has_required_keys():
    bundle = build_move_fact_bundle(BASE_MOVE, user_color="white", motifs=[], features={"phase": "opening"})
    for key in (
        "move_san",
        "fen",
        "legal_moves",
        "multipv",
        "win_percent_before",
        "motifs",
        "features",
        "user_perspective",
        "maia",
    ):
        assert key in bundle


def test_user_perspective_true_when_user_played():
    bundle = build_move_fact_bundle(BASE_MOVE, user_color="white", motifs=[], features={})
    assert bundle["user_perspective"] is True


def test_user_perspective_false_when_opponent_played():
    bundle = build_move_fact_bundle(BASE_MOVE, user_color="black", motifs=[], features={})
    assert bundle["user_perspective"] is False


def test_legal_moves_includes_played_move():
    bundle = build_move_fact_bundle(BASE_MOVE, user_color="white", motifs=[], features={})
    assert "e4" in bundle["legal_moves"]


def test_maia_substructure_passed_through():
    bundle = build_move_fact_bundle(BASE_MOVE, user_color="white", motifs=[], features={})
    assert bundle["maia"]["top1_san"] == "e4"
    assert bundle["maia"]["match_played"] is True
