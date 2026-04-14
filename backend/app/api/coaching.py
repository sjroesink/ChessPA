import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.game import Game
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
