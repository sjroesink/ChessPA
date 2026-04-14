from app.analysis.openings import classify_opening


def test_ruy_lopez_detected():
    eco, name = classify_opening(["e4", "e5", "Nf3", "Nc6", "Bb5"])
    assert eco is not None
    assert eco.startswith("C")
    assert "Ruy Lopez" in name or "Spanish" in name


def test_italian_game_detected():
    eco, name = classify_opening(["e4", "e5", "Nf3", "Nc6", "Bc4"])
    assert eco is not None
    assert "Italian" in name or eco.startswith("C")


def test_sicilian_detected():
    eco, name = classify_opening(["e4", "c5"])
    assert eco is not None
    assert "Sicilian" in name


def test_obscure_start_returns_none_or_a00():
    eco, _ = classify_opening(["h4", "h5"])
    assert eco is None or eco.startswith("A0")


def test_empty_moves_returns_none():
    eco, name = classify_opening([])
    assert eco is None and name is None


def test_longest_prefix_preferred():
    short_eco, short_name = classify_opening(["e4", "e5"])
    long_eco, long_name = classify_opening(["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4"])
    # Longer sequence should resolve to a more specific (longer) name
    assert long_name is not None
    assert short_name is None or len(long_name) >= len(short_name)
