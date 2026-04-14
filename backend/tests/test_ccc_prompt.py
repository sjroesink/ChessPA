from app.analysis.ccc_prompt import build_prompt, validate_commentary


BUNDLE = {
    "move_san": "Bxc2",
    "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPPQPPP/RNB1KB1R w KQkq - 0 1",
    "legal_moves": ["Nxd4", "Bxc2", "a6", "Nc3"],
    "classification": "blunder",
    "best_move_san": "Nxd4",
    "eval_before_cp": 20,
    "eval_after_cp": -180,
    "centipawn_loss": 200,
    "win_percent_before": 55.0,
    "win_percent_after": 30.0,
    "accuracy_percent": 20.0,
    "is_critical_moment": True,
    "multipv": [
        {"rank": 1, "san": "Nxd4", "pv_san": ["Nxd4", "Bxd4", "c5"], "eval_cp": 50},
    ],
    "motifs": [{"type": "hanging", "square": "c2"}],
    "features": {"phase": "middlegame"},
    "user_perspective": True,
    "maia": {"top1_san": "Bxc2", "top1_prob": 0.42, "match_played": True, "rating_used": 1700},
}


def test_prompt_contains_facts_and_rules():
    prompt = build_prompt(BUNDLE, user_color="black")
    assert "Nederlands" in prompt
    assert "Bxc2" in prompt
    assert "Nxd4" in prompt
    assert "hangend" in prompt or "hanging" in prompt.lower()
    assert "middlegame" in prompt


def test_prompt_flags_maia_trap_on_blunder():
    prompt = build_prompt(BUNDLE, user_color="black")
    assert "Maia" in prompt
    assert "valstrik" in prompt


def test_validator_accepts_legal_mention():
    ok, reason = validate_commentary("Bxc2 liet het stuk hangen; beter was Nxd4.", BUNDLE)
    assert ok, reason


def test_validator_rejects_illegal_move():
    # Qxh7 is a legal-looking SAN but not in the allowed vocabulary for this bundle.
    ok, reason = validate_commentary("Beter was Qxh7 geweest.", BUNDLE)
    assert ok is False
    assert "Qxh7" in reason


def test_validator_accepts_pv_continuation_moves():
    ok, reason = validate_commentary("Na Nxd4 volgt Bxd4 en c5 wint een pion.", BUNDLE)
    assert ok, reason


def test_validator_accepts_plain_text_without_moves():
    ok, _ = validate_commentary("Dit gaf een stuk weg zonder compensatie.", BUNDLE)
    assert ok
