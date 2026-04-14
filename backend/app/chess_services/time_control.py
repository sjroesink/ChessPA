def classify_time_control(time_control: str | None) -> str:
    """Classify time control string into bullet/blitz/rapid/classical/unknown.

    Time control format: "base" or "base+increment" in seconds.
    Thresholds (effective time = base + 40 * increment):
      bullet:    < 180s
      blitz:     180s - 599s
      rapid:     600s - 1800s
      classical: > 1800s
    """
    if not time_control or time_control.strip() in ("", "-"):
        return "unknown"

    try:
        parts = time_control.split("+")
        base = int(parts[0])
        increment = int(parts[1]) if len(parts) > 1 else 0
        effective = base + 40 * increment
    except (ValueError, IndexError):
        return "unknown"

    if effective < 180:
        return "bullet"
    elif effective < 600:
        return "blitz"
    elif effective <= 1800:
        return "rapid"
    else:
        return "classical"
