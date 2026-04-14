import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.game import Game
from app.models.game_summary import GameSummary
from app.models.move_analysis import MoveAnalysis
from app.models.coaching_insight import CoachingInsight
from app.auth.dependencies import get_current_user
from app.coaching.service import generate_coaching_insights

router = APIRouter(prefix="/api/coaching", tags=["coaching"])


@router.get("/insights")
async def list_insights(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CoachingInsight)
        .where(CoachingInsight.user_id == user.id)
        .order_by(CoachingInsight.generated_at.desc())
    )
    insights = result.scalars().all()

    return [
        {
            "id": str(i.id),
            "type": i.type,
            "title": i.title,
            "description": i.description,
            "severity": i.severity,
            "related_games": [str(gid) for gid in (i.related_games or [])],
            "generated_at": i.generated_at.isoformat() if i.generated_at else None,
            "model_version": i.model_version,
        }
        for i in insights
    ]


@router.post("/refresh")
async def refresh_insights(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        insights = await generate_coaching_insights(db, user.id)
        return {
            "status": "ok",
            "insights_generated": len(insights),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")


@router.get("/insights/{insight_id}")
async def get_insight(
    insight_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CoachingInsight).where(
            CoachingInsight.id == uuid.UUID(insight_id),
            CoachingInsight.user_id == user.id,
        )
    )
    insight = result.scalar_one_or_none()
    if insight is None:
        raise HTTPException(status_code=404, detail="Insight not found")

    # Fetch related games
    related_games_data = []
    if insight.related_games:
        games_result = await db.execute(
            select(Game).where(Game.id.in_(insight.related_games))
        )
        for g in games_result.scalars().all():
            opponent = g.black_username if g.user_color == "white" else g.white_username
            related_games_data.append({
                "id": str(g.id),
                "opponent": opponent,
                "result": g.result,
                "opening_name": g.opening_name,
                "played_at": g.played_at.isoformat() if g.played_at else None,
            })

    return {
        "id": str(insight.id),
        "type": insight.type,
        "title": insight.title,
        "description": insight.description,
        "severity": insight.severity,
        "related_games": related_games_data,
        "generated_at": insight.generated_at.isoformat() if insight.generated_at else None,
        "model_version": insight.model_version,
    }


@router.get("/weaknesses")
async def weaknesses(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate per-user weaknesses across all analyzed games.

    Returns per-opening accuracy, per-phase ACPL, and top missed motifs
    (motifs seen on the board during mistakes/blunders).
    """
    games_result = await db.execute(select(Game).where(Game.user_id == user.id))
    games = games_result.scalars().all()
    if not games:
        return {
            "games_analyzed": 0,
            "per_opening": [],
            "per_phase": {},
            "top_motifs": [],
        }

    game_ids = [g.id for g in games]
    game_color: dict[uuid.UUID, str] = {g.id: g.user_color for g in games}

    summaries_result = await db.execute(
        select(GameSummary).where(GameSummary.game_id.in_(game_ids))
    )
    summaries = summaries_result.scalars().all()

    eco_acc: dict[str, list[float]] = {}
    eco_name: dict[str, str] = {}
    for s in summaries:
        if not s.opening_eco:
            continue
        user_color = game_color.get(s.game_id)
        if user_color == "white" and s.accuracy_white is not None:
            eco_acc.setdefault(s.opening_eco, []).append(s.accuracy_white)
        elif user_color == "black" and s.accuracy_black is not None:
            eco_acc.setdefault(s.opening_eco, []).append(s.accuracy_black)
        eco_name.setdefault(s.opening_eco, s.opening_name or s.opening_eco)

    per_opening = [
        {
            "eco": eco,
            "name": eco_name[eco],
            "games": len(values),
            "avg_accuracy": round(sum(values) / len(values), 1),
        }
        for eco, values in eco_acc.items()
    ]
    per_opening.sort(key=lambda r: r["avg_accuracy"])

    phase_sums: dict[str, list[float]] = {}
    for s in summaries:
        if s.phase_acpl:
            for phase, cpl in s.phase_acpl.items():
                phase_sums.setdefault(phase, []).append(cpl)
    per_phase = {p: round(sum(v) / len(v), 1) for p, v in phase_sums.items()}

    moves_result = await db.execute(
        select(MoveAnalysis)
        .where(MoveAnalysis.game_id.in_(game_ids))
        .where(MoveAnalysis.classification.in_(("mistake", "blunder")))
    )
    motif_counter: Counter = Counter()
    for m in moves_result.scalars().all():
        motifs = (m.details_json or {}).get("motifs", [])
        for motif in motifs:
            motif_counter[motif.get("type", "unknown")] += 1

    top_motifs = [{"type": t, "count": c} for t, c in motif_counter.most_common(10)]

    return {
        "games_analyzed": len(summaries),
        "per_opening": per_opening,
        "per_phase": per_phase,
        "top_motifs": top_motifs,
    }
