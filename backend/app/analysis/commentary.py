"""Per-move LLM commentary via CCC-framework prompt + legal-move validator."""

from app.analysis.ccc_prompt import build_prompt, validate_commentary
from app.analysis.facts import build_move_fact_bundle
from app.config import settings
from app.llm.provider import get_llm_provider


SYSTEM_PROMPT = (
    "Je bent een schaakcoach voor een speler rond {user_color_label}-Elo. Spreek Nederlands, "
    "kort en concreet, vanuit het perspectief van de speler. Houd je strikt aan de feiten."
)


async def generate_single_comment(bundle: dict, user_color: str) -> str | None:
    """Run CCC prompt + one validator-retry against the configured LLM provider."""
    llm = get_llm_provider()
    system = SYSTEM_PROMPT.format(user_color_label="wit" if user_color == "white" else "zwart")
    prompt = build_prompt(bundle, user_color)
    for attempt in range(2):
        text = await llm.generate(system, prompt)
        ok, reason = validate_commentary(text, bundle)
        if ok:
            return text.strip()
        prompt += (
            f"\n\nFOUT IN VORIGE POGING: {reason}. "
            "Probeer opnieuw, noem alleen zetten uit de toegestane lijst."
        )
    return None


async def generate_move_commentary(
    moves: list[dict],
    user_color: str,
) -> dict[tuple[int, str], str]:
    """Generate commentary for every significant move (inaccuracy+) and every critical moment."""
    threshold = settings.llm_commentary_threshold
    targets: list[dict] = []
    for m in moves:
        cpl = abs(m.get("centipawn_loss", 0) or 0)
        is_bad = cpl >= threshold or m.get("classification") in ("inaccuracy", "mistake", "blunder")
        is_critical = bool(m.get("is_critical_moment"))
        if is_bad or is_critical:
            targets.append(m)

    if not targets:
        return {}

    result: dict[tuple[int, str], str] = {}
    for m in targets:
        try:
            motifs = (m.get("details") or {}).get("motifs") or m.get("motifs") or []
            features = (m.get("details") or {}).get("features") or m.get("features") or {}
            bundle = build_move_fact_bundle(m, user_color, motifs, features)
            comment = await generate_single_comment(bundle, user_color)
            if comment:
                result[(m["move_number"], m["color"])] = comment
        except Exception as exc:  # pragma: no cover - runtime resilience
            print(f"Commentary error on move {m.get('move_number')}: {exc}")
    return result
