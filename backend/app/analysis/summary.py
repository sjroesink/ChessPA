"""Game-level aggregation: accuracy per colour, phase ACPL, opening, motif counts."""

from collections import Counter, defaultdict

from app.analysis.openings import classify_opening


def detect_phase(move_number: int, total_moves: int) -> str:
    if total_moves == 0:
        return "opening"
    ratio = move_number / total_moves
    if ratio <= 0.25:
        return "opening"
    if ratio <= 0.75:
        return "middlegame"
    return "endgame"


def _phase_for_row(row: dict) -> str:
    # Prefer per-move phase from positional features when present.
    features = row.get("features") or {}
    phase = features.get("phase")
    if phase:
        return phase
    return detect_phase(row.get("move_number", 0), row.get("total_moves", 0))


def compute_game_summary(
    move_analyses: list[dict],
    opening_moves_san: list[str] | None = None,
) -> dict:
    if not move_analyses:
        return {
            "blunders": 0,
            "mistakes": 0,
            "inaccuracies": 0,
            "avg_eval_loss": 0.0,
            "phase_scores": {"opening": 100, "middlegame": 100, "endgame": 100},
            "time_trouble": False,
            "accuracy_white": None,
            "accuracy_black": None,
            "opening_eco": None,
            "opening_name": None,
            "phase_acpl": {},
            "motif_counts": {},
        }

    blunders = sum(1 for m in move_analyses if m["classification"] == "blunder")
    mistakes = sum(1 for m in move_analyses if m["classification"] == "mistake")
    inaccuracies = sum(1 for m in move_analyses if m["classification"] == "inaccuracy")

    # Support both new (`centipawn_loss`) and legacy (`eval_loss`) keys.
    def _cpl(row: dict) -> float:
        if "centipawn_loss" in row and row["centipawn_loss"] is not None:
            return float(row["centipawn_loss"])
        return float(row.get("eval_loss", 0) or 0)

    avg_eval_loss = sum(_cpl(m) for m in move_analyses) / len(move_analyses)

    # Per-colour accuracy (arithmetic mean of accuracy_percent when present).
    white_acc = [m["accuracy_percent"] for m in move_analyses if m.get("color") == "white" and m.get("accuracy_percent") is not None]
    black_acc = [m["accuracy_percent"] for m in move_analyses if m.get("color") == "black" and m.get("accuracy_percent") is not None]
    accuracy_white = sum(white_acc) / len(white_acc) if white_acc else None
    accuracy_black = sum(black_acc) / len(black_acc) if black_acc else None

    # Phase ACPL: average centipawn loss per phase.
    phase_losses: dict[str, list[float]] = defaultdict(list)
    for m in move_analyses:
        phase_losses[_phase_for_row(m)].append(_cpl(m))
    phase_acpl = {p: (sum(v) / len(v)) for p, v in phase_losses.items() if v}

    # Legacy phase_scores (100 - acpl, clamped) retained for backward compatibility.
    phase_scores: dict[str, float] = {}
    for phase in ("opening", "middlegame", "endgame"):
        losses = phase_losses.get(phase, [])
        if losses:
            phase_scores[phase] = max(0, round(100 - sum(losses) / len(losses), 1))
        else:
            phase_scores[phase] = 100

    # Motif frequency counter (flattened across all moves).
    motif_counter: Counter = Counter()
    for m in move_analyses:
        motifs = m.get("motifs") or []
        for motif in motifs:
            motif_counter[motif.get("type", "unknown")] += 1

    eco = name = None
    if opening_moves_san:
        eco, name = classify_opening(opening_moves_san)

    return {
        "blunders": blunders,
        "mistakes": mistakes,
        "inaccuracies": inaccuracies,
        "avg_eval_loss": round(avg_eval_loss, 2),
        "phase_scores": phase_scores,
        "time_trouble": False,
        "accuracy_white": accuracy_white,
        "accuracy_black": accuracy_black,
        "opening_eco": eco,
        "opening_name": name,
        "phase_acpl": phase_acpl,
        "motif_counts": dict(motif_counter),
    }
