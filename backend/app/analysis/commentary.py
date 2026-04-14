"""Per-move LLM commentary for significant errors, from the user's perspective."""

import json

from app.config import settings
from app.llm.provider import get_llm_provider


SINGLE_SYSTEM_PROMPT = """Je bent een schaakcoach voor een ~1700 Elo speler. Je geeft commentaar VANUIT HET PERSPECTIEF VAN DE SPELER.

Context: de speler speelt met {user_color}. Je krijgt één zet die significant verschilt van de beste zet.

REGELS:
- Maximum 1-2 zinnen, heel kort en concreet
- Nederlandse taal
- Als het een EIGEN zet is: leg uit wat er fout ging (bijv. "je geeft een pion weg", "je laat de diagonaal zwak")
- Als het een TEGENSTANDER-zet is: leg uit wat het voor JOU betekent (bijv. "tegenstander geeft een pion weg — jouw kans", "tegenstander geeft de open lijn prijs")
- Noem ALTIJD één of meer concrete zetten (bijv. Bd3, Nxe5, Qxa2) als referentie
- Géén algemene adviezen, géén "je moet nadenken over" clichés
- Géén inleiding, direct to the point"""


BATCH_SYSTEM_PROMPT = """Je bent een schaakcoach voor een ~1700 Elo speler. Je geeft commentaar VANUIT HET PERSPECTIEF VAN DE SPELER.

Context: de speler speelt met {user_color}. Je krijgt meerdere zetten uit één partij waar significant van de beste zet is afgeweken.

REGELS per zet:
- Maximum 1-2 zinnen, heel kort en concreet
- Nederlandse taal
- Als het een EIGEN zet is: leg uit wat er fout ging (bijv. "je geeft een pion weg", "je laat de diagonaal zwak")
- Als het een TEGENSTANDER-zet is: leg uit wat het voor JOU betekent (bijv. "tegenstander geeft een pion weg — jouw kans", "tegenstander geeft de open lijn prijs")
- Noem ALTIJD één of meer concrete zetten (bijv. Bd3, Nxe5, Qxa2) als referentie
- Géén algemene adviezen, géén "je moet nadenken over" clichés

ANTWOORD ALLEEN MET GELDIGE JSON in dit exacte formaat:
{{
  "comments": [
    {{"move_number": 14, "color": "white", "comment": "..."}},
    {{"move_number": 23, "color": "black", "comment": "..."}}
  ]
}}"""


def _format_move_context(move: dict, user_color: str) -> str:
    cp_loss = abs(move["centipawn_loss"])
    eval_before = move["eval_before"] / 100
    eval_after = move["eval_after"] / 100
    is_user = move["color"] == user_color
    who = "JOUW zet" if is_user else "TEGENSTANDER-zet"
    return (
        f"Zet {move['move_number']} ({move['color']}) — {who}: "
        f"{move['move_san']} (gespeeld) vs {move['best_move_san']} (best)\n"
        f"FEN: {move['fen']}\n"
        f"Eval: {eval_before:+.1f} → {eval_after:+.1f} (verlies: {cp_loss/100:.1f} pion)"
    )


async def generate_single_comment(move: dict, user_color: str) -> str:
    """Generate commentary for a single move (Ollama-friendly)."""
    llm = get_llm_provider()
    system = SINGLE_SYSTEM_PROMPT.format(user_color="wit" if user_color == "white" else "zwart")
    user_prompt = _format_move_context(move, user_color)
    return await llm.generate(system, user_prompt)


async def generate_batch_comments(moves: list[dict], user_color: str) -> dict[tuple[int, str], str]:
    """Generate commentary for multiple moves in one call (Claude-friendly)."""
    llm = get_llm_provider()
    system = BATCH_SYSTEM_PROMPT.format(user_color="wit" if user_color == "white" else "zwart")
    user_prompt = "Analyseer deze zetten:\n\n" + "\n\n".join(
        f"### Positie {i+1}\n{_format_move_context(m, user_color)}"
        for i, m in enumerate(moves)
    )

    raw = await llm.generate(system, user_prompt)

    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        return {}

    result = {}
    for item in data.get("comments", []):
        key = (item["move_number"], item["color"])
        result[key] = item["comment"]
    return result


async def generate_move_commentary(moves: list[dict], user_color: str) -> dict[tuple[int, str], str]:
    """Generate commentary for significant errors using configured mode."""
    threshold = settings.llm_commentary_threshold
    bad_moves = [m for m in moves if abs(m["centipawn_loss"]) >= threshold]

    if not bad_moves:
        return {}

    mode = settings.llm_commentary_mode

    if mode == "batch":
        return await generate_batch_comments(bad_moves, user_color)

    result = {}
    for m in bad_moves:
        try:
            comment = await generate_single_comment(m, user_color)
            result[(m["move_number"], m["color"])] = comment.strip()
        except Exception as e:
            print(f"Commentary error for move {m['move_number']}: {e}")
    return result
