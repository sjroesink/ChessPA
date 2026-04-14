def detect_phase(move_number: int, total_moves: int) -> str:
    if total_moves == 0:
        return "opening"
    ratio = move_number / total_moves
    if ratio <= 0.25:
        return "opening"
    elif ratio <= 0.75:
        return "middlegame"
    else:
        return "endgame"

def compute_game_summary(move_analyses: list[dict]) -> dict:
    if not move_analyses:
        return {
            "blunders": 0, "mistakes": 0, "inaccuracies": 0,
            "avg_eval_loss": 0.0,
            "phase_scores": {"opening": 100, "middlegame": 100, "endgame": 100},
            "time_trouble": False,
        }

    blunders = sum(1 for m in move_analyses if m["classification"] == "blunder")
    mistakes = sum(1 for m in move_analyses if m["classification"] == "mistake")
    inaccuracies = sum(1 for m in move_analyses if m["classification"] == "inaccuracy")
    avg_eval_loss = sum(m["eval_loss"] for m in move_analyses) / len(move_analyses)

    phase_moves: dict[str, list[float]] = {"opening": [], "middlegame": [], "endgame": []}
    for m in move_analyses:
        phase = detect_phase(m["move_number"], m["total_moves"])
        phase_moves[phase].append(m["eval_loss"])

    phase_scores = {}
    for phase, losses in phase_moves.items():
        if losses:
            phase_scores[phase] = max(0, round(100 - sum(losses) / len(losses), 1))
        else:
            phase_scores[phase] = 100

    return {
        "blunders": blunders, "mistakes": mistakes, "inaccuracies": inaccuracies,
        "avg_eval_loss": round(avg_eval_loss, 2),
        "phase_scores": phase_scores,
        "time_trouble": False,
    }
