"""Lichess-style win%, accuracy%, and move-label scoring.

Formulas from https://lichess.org/page/accuracy (public spec).
"""

import math
from typing import Literal, Optional

Label = Literal["inaccuracy", "mistake", "blunder"]


def win_percent_from_cp(cp: float) -> float:
    """Convert centipawn eval (side-to-move perspective) to win-probability percent (0-100)."""
    # Clamp extreme values so math.exp doesn't overflow on mate scores.
    cp = max(-10000.0, min(10000.0, cp))
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def accuracy_from_win_delta(win_drop_percent: float) -> float:
    """Lichess per-move accuracy from win% drop (win_before - win_after, 0-100 scale)."""
    drop = max(0.0, win_drop_percent)
    value = 103.1668 * math.exp(-0.04354 * drop) - 3.1669
    return max(0.0, min(100.0, value))


def label_from_win_drop(win_drop_percent: float) -> Optional[Label]:
    """Classify move from win% drop using Lichess thresholds."""
    if win_drop_percent >= 30:
        return "blunder"
    if win_drop_percent >= 20:
        return "mistake"
    if win_drop_percent >= 10:
        return "inaccuracy"
    return None


def game_accuracy(accuracies: list[float]) -> float:
    """Simple arithmetic mean across per-move accuracies (Lichess uses a weighted mean; good-enough baseline)."""
    if not accuracies:
        return 0.0
    return sum(accuracies) / len(accuracies)
