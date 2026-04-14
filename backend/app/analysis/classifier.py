def classify_move(centipawn_loss: float) -> str:
    cp = abs(centipawn_loss)
    if cp <= 10:
        return "best"
    elif cp <= 25:
        return "good"
    elif cp <= 50:
        return "inaccuracy"
    elif cp <= 100:
        return "mistake"
    else:
        return "blunder"
