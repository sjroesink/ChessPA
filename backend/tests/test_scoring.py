import pytest

from app.analysis.scoring import (
    accuracy_from_win_delta,
    game_accuracy,
    label_from_win_drop,
    win_percent_from_cp,
)


def test_win_percent_zero_cp_is_fifty():
    assert win_percent_from_cp(0) == pytest.approx(50.0, abs=0.01)


def test_win_percent_monotonic_increasing():
    assert win_percent_from_cp(100) > win_percent_from_cp(0)
    assert win_percent_from_cp(1000) > win_percent_from_cp(100)


def test_win_percent_negative_is_below_fifty():
    assert win_percent_from_cp(-100) < 50.0


def test_win_percent_mate_saturates():
    assert win_percent_from_cp(10000) > 99.0
    assert win_percent_from_cp(-10000) < 1.0


def test_accuracy_full_when_no_drop():
    assert accuracy_from_win_delta(0) == pytest.approx(100.0, abs=0.5)


def test_accuracy_decreases_with_drop():
    assert accuracy_from_win_delta(50) < accuracy_from_win_delta(10)


def test_accuracy_clamped_to_zero_on_huge_drop():
    assert accuracy_from_win_delta(200) == pytest.approx(0.0, abs=0.5)


@pytest.mark.parametrize(
    "drop,expected",
    [
        (5, None),
        (10, "inaccuracy"),
        (15, "inaccuracy"),
        (20, "mistake"),
        (29, "mistake"),
        (30, "blunder"),
        (99, "blunder"),
    ],
)
def test_label_from_win_drop(drop, expected):
    assert label_from_win_drop(drop) == expected


def test_game_accuracy_empty_is_zero():
    assert game_accuracy([]) == 0.0


def test_game_accuracy_mean():
    assert game_accuracy([80.0, 90.0, 100.0]) == pytest.approx(90.0, abs=0.01)
