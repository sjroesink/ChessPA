import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.game import Game
from app.models.game_summary import GameSummary
from app.models.coaching_insight import CoachingInsight
from app.llm.provider import get_llm_provider
from app.coaching.prompts import SYSTEM_PROMPT, build_user_prompt
from app.coaching.schemas import CoachingResponse


async def generate_coaching_insights(
    db: AsyncSession,
    user_id: uuid.UUID,
    max_games: int = 50,
) -> list[CoachingInsight]:
    """Generate coaching insights for a user from their recent analyzed games."""

    # 1. Fetch recent analyzed games
    result = await db.execute(
        select(Game)
        .where(Game.user_id == user_id, Game.analysis_status == "done")
        .order_by(Game.played_at.desc())
        .limit(max_games)
    )
    games = result.scalars().all()

    if len(games) < 3:
        return []  # Not enough data

    # 2. Fetch summaries for these games
    game_ids = [g.id for g in games]
    summary_result = await db.execute(
        select(GameSummary).where(GameSummary.game_id.in_(game_ids))
    )
    summaries = {s.game_id: s for s in summary_result.scalars().all()}

    # 3. Aggregate stats
    total = len(games)
    wins = sum(1 for g in games if g.result == "win")
    winrate = round(wins / total * 100, 1) if total > 0 else 0

    # Most recent elo
    elo = games[0].user_elo if games else None

    # Opening stats
    opening_counts: dict[str, dict] = {}
    for g in games:
        name = g.opening_name or "Unknown"
        if name not in opening_counts:
            opening_counts[name] = {"total": 0, "wins": 0, "draws": 0, "losses": 0}
        opening_counts[name]["total"] += 1
        opening_counts[name][
            {"win": "wins", "loss": "losses", "draw": "draws"}.get(g.result, "draws")
        ] += 1

    opening_stats = sorted(
        [
            {
                "opening": name,
                "total": s["total"],
                "wins": s["wins"],
                "draws": s["draws"],
                "losses": s["losses"],
                "winrate": round(s["wins"] / s["total"] * 100, 1)
                if s["total"] > 0
                else 0,
            }
            for name, s in opening_counts.items()
        ],
        key=lambda x: x["total"],
        reverse=True,
    )

    # Phase scores
    phase_totals: dict[str, list[float]] = {
        "opening": [],
        "middlegame": [],
        "endgame": [],
    }
    total_blunders = 0
    total_mistakes = 0
    total_inaccuracies = 0
    eval_losses = []

    for g in games:
        s = summaries.get(g.id)
        if s:
            total_blunders += s.blunders
            total_mistakes += s.mistakes
            total_inaccuracies += s.inaccuracies
            eval_losses.append(s.avg_eval_loss)
            if s.phase_scores:
                for phase in ("opening", "middlegame", "endgame"):
                    if phase in s.phase_scores:
                        phase_totals[phase].append(s.phase_scores[phase])

    phase_scores = {
        phase: round(sum(vals) / len(vals), 1) if vals else None
        for phase, vals in phase_totals.items()
    }

    blunder_stats = {
        "total_blunders": total_blunders,
        "total_mistakes": total_mistakes,
        "total_inaccuracies": total_inaccuracies,
        "avg_eval_loss": sum(eval_losses) / len(eval_losses) if eval_losses else 0,
    }

    # Recent games for prompt
    recent_games_data = []
    for g in games[:20]:
        opponent = g.black_username if g.user_color == "white" else g.white_username
        s = summaries.get(g.id)
        recent_games_data.append(
            {
                "result": g.result,
                "opponent": opponent,
                "opening": g.opening_name,
                "blunders": s.blunders if s else None,
                "phase": f"O:{s.phase_scores.get('opening', '?')}/M:{s.phase_scores.get('middlegame', '?')}/E:{s.phase_scores.get('endgame', '?')}"
                if s and s.phase_scores
                else None,
            }
        )

    # 4. Build prompt
    user_prompt = build_user_prompt(
        elo=elo,
        total_games=total,
        winrate=winrate,
        opening_stats=opening_stats,
        phase_scores=phase_scores,
        blunder_stats=blunder_stats,
        recent_games=recent_games_data,
    )

    # 5. Call LLM
    provider = get_llm_provider()
    raw_response = await provider.generate(SYSTEM_PROMPT, user_prompt)

    # 6. Parse response
    try:
        # Strip markdown code fences if present
        text = raw_response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        parsed = CoachingResponse.model_validate_json(text)
    except Exception:
        # Try to extract JSON from response
        try:
            start = raw_response.index("{")
            end = raw_response.rindex("}") + 1
            parsed = CoachingResponse.model_validate_json(raw_response[start:end])
        except Exception:
            return []

    # 7. Delete old insights for this user
    await db.execute(
        delete(CoachingInsight).where(CoachingInsight.user_id == user_id)
    )

    # 8. Persist new insights
    model_version = (
        settings.anthropic_model
        if settings.llm_provider == "claude"
        else settings.ollama_model
    )
    new_insights = []

    for insight_data in parsed.insights[:5]:
        # Map game indices to actual game IDs
        related_ids = []
        for idx in insight_data.related_game_indices:
            if 0 <= idx < len(games):
                related_ids.append(games[idx].id)

        insight = CoachingInsight(
            user_id=user_id,
            type=insight_data.type,
            title=insight_data.title,
            description=insight_data.description,
            severity=insight_data.severity,
            related_games=related_ids,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            model_version=model_version,
        )
        db.add(insight)
        new_insights.append(insight)

    await db.commit()
    for insight in new_insights:
        await db.refresh(insight)

    return new_insights
