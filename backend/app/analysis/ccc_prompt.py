"""Concept-guided Chess Commentary (CCC) prompt + output validator.

The prompt anchors the LLM to engine-grounded facts so it only verbalises
conclusions that are already in the bundle (MultiPV, motifs, Maia, Win%).

The validator then rejects any move reference in the output that is not a
legal move in the position or part of the MultiPV/best-move vocabulary.
"""

from __future__ import annotations

import re

SAN_REGEX = re.compile(
    r"\b("
    r"[KQRBN][a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?"
    r"|O-O-O|O-O"
    r"|[a-h]x[a-h][1-8](?:=[QRBN])?[+#]?"
    r"|[a-h][1-8](?:=[QRBN])?[+#]?"
    r")\b"
)


def _motif_labels(motifs: list[dict]) -> str:
    if not motifs:
        return "geen"
    parts: list[str] = []
    for m in motifs:
        t = m["type"]
        if t == "fork":
            parts.append(f"vork op {m.get('attacker', '?')}")
        elif t in ("absolute_pin", "relative_pin"):
            parts.append(f"penning {m.get('pinned', '?')}→{m.get('target', '?')}")
        elif t == "skewer":
            parts.append(f"spies {m.get('front', '?')}→{m.get('back', '?')}")
        elif t == "hanging":
            parts.append(f"hangend stuk op {m.get('square', '?')}")
        else:
            parts.append(t)
    return ", ".join(parts)


def build_prompt(bundle: dict, user_color: str) -> str:
    user_perspective = bundle.get("user_perspective")
    speaker = "JIJ" if user_perspective else "TEGENSTANDER"
    pv = bundle["multipv"][0] if bundle.get("multipv") else {}
    pv_san = " ".join(pv.get("pv_san", [])[:4]) or bundle["best_move_san"]
    maia = bundle.get("maia") or {}
    maia_line = ""
    if maia.get("match_played") and bundle["classification"] in ("blunder", "mistake"):
        maia_line = (
            f"Maia-{maia.get('rating_used')} voorspelt precies deze fout → "
            f"typische menselijke valstrik op dit niveau."
        )

    features = bundle.get("features") or {}
    phase = features.get("phase", "?")
    motif_line = _motif_labels(bundle.get("motifs") or [])

    wb = bundle.get("win_percent_before")
    wa = bundle.get("win_percent_after")
    win_line = ""
    if wb is not None and wa is not None:
        win_line = f"Win% {wb:.0f} → {wa:.0f}"

    return f"""Je bent een schaakcoach. Schrijf in het Nederlands, maximaal 2 zinnen, vanuit het perspectief van de speler (speler speelt: {user_color}).

FEITEN (niet verzinnen, niet uitbreiden):
- Gespeelde zet: {bundle['move_san']} — door {speaker}
- Classificatie: {bundle['classification']}
- {win_line}
- Beste alternatief: {bundle['best_move_san']} (PV: {pv_san})
- Motieven op het bord: {motif_line}
- Fase: {phase}
- Kritiek moment: {"ja" if bundle.get('is_critical_moment') else "nee"}
- {maia_line}

REGELS:
- Noem alleen zetten die in deze lijst staan: {bundle['move_san']}, {bundle['best_move_san']}, {', '.join(s for s in pv.get('pv_san', [])[:3])}.
- Maximaal 2 zinnen. Concreet en actiegericht.
- Als {speaker} = JIJ: leg uit wat JIJ verloor of miste.
- Als {speaker} = TEGENSTANDER: leg uit wat het voor JOU betekent (kans of bedreiging).
- Geen clichés, geen inleiding, geen samenvatting."""


def validate_commentary(text: str, bundle: dict) -> tuple[bool, str]:
    """Reject commentary that mentions SAN moves outside the allowed vocabulary."""
    allowed: set[str] = set(bundle.get("legal_moves") or [])
    for pv in bundle.get("multipv") or []:
        for san in pv.get("pv_san", []):
            allowed.add(san)
        if pv.get("san"):
            allowed.add(pv["san"])
    allowed.add(bundle.get("best_move_san", ""))
    allowed.add(bundle.get("move_san", ""))

    for match in SAN_REGEX.findall(text):
        if match not in allowed:
            return False, f"illegal move mentioned: {match}"
    return True, ""
