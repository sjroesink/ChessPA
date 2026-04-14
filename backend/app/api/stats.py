from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.game import Game
from app.models.game_summary import GameSummary
from app.auth.dependencies import get_current_user
from app.chess_services.time_control import classify_time_control

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _base_query(user_id, days: int | None = None):
    """Build base game query with optional time filter."""
    q = select(Game).where(Game.user_id == user_id)
    if days:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        q = q.where(Game.played_at >= since)
    return q


@router.get("/overview")
async def overview(
    days: int = Query(30, ge=1, le=365),
    time_category: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    base = select(Game).where(Game.user_id == user.id, Game.played_at >= since)

    result = await db.execute(base)
    games = result.scalars().all()

    # Filter by time_category in Python (derived field)
    if time_category:
        games = [g for g in games if classify_time_control(g.time_control) == time_category]

    total = len(games)
    if total == 0:
        return {"total_games": 0, "winrate": 0, "current_elo": None, "avg_accuracy": None}

    wins = sum(1 for g in games if g.result == "win")
    winrate = round(wins / total * 100, 1)

    # Current elo = most recent game's elo
    sorted_games = sorted(games, key=lambda g: g.played_at, reverse=True)
    current_elo = sorted_games[0].user_elo

    # Avg accuracy from summaries
    game_ids = [g.id for g in games if g.analysis_status == "done"]
    avg_accuracy = None
    if game_ids:
        summary_result = await db.execute(
            select(func.avg(GameSummary.avg_eval_loss))
            .where(GameSummary.game_id.in_(game_ids))
        )
        avg_loss = summary_result.scalar()
        if avg_loss is not None:
            avg_accuracy = round(max(0, 100 - avg_loss), 1)

    return {
        "total_games": total,
        "winrate": winrate,
        "current_elo": current_elo,
        "avg_accuracy": avg_accuracy,
    }


@router.get("/openings")
async def openings(
    days: int = Query(90, ge=1, le=365),
    time_category: str | None = None,
    limit: int = Query(10, ge=1, le=30),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Game).where(Game.user_id == user.id, Game.played_at >= since)
    )
    games = result.scalars().all()

    if time_category:
        games = [g for g in games if classify_time_control(g.time_control) == time_category]

    # Group by opening
    opening_stats: dict[str, dict] = {}
    for g in games:
        name = g.opening_name or "Unknown"
        if name not in opening_stats:
            opening_stats[name] = {"total": 0, "wins": 0, "draws": 0, "losses": 0}
        opening_stats[name]["total"] += 1
        if g.result == "win":
            opening_stats[name]["wins"] += 1
        elif g.result == "draw":
            opening_stats[name]["draws"] += 1
        else:
            opening_stats[name]["losses"] += 1

    # Sort by total games, take top N
    sorted_openings = sorted(opening_stats.items(), key=lambda x: x[1]["total"], reverse=True)[:limit]

    return [
        {
            "opening": name,
            "total": stats["total"],
            "wins": stats["wins"],
            "draws": stats["draws"],
            "losses": stats["losses"],
            "winrate": round(stats["wins"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0,
        }
        for name, stats in sorted_openings
    ]


@router.get("/elo-history")
async def elo_history(
    days: int = Query(90, ge=1, le=365),
    time_category: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Game)
        .where(Game.user_id == user.id, Game.played_at >= since)
        .order_by(Game.played_at)
    )
    games = result.scalars().all()

    if time_category:
        games = [g for g in games if classify_time_control(g.time_control) == time_category]

    return [
        {
            "date": g.played_at.isoformat() if g.played_at else None,
            "elo": g.user_elo,
            "result": g.result,
        }
        for g in games if g.user_elo is not None
    ]


@router.get("/phases")
async def phases(
    days: int = Query(90, ge=1, le=365),
    time_category: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Game).where(
            Game.user_id == user.id,
            Game.played_at >= since,
            Game.analysis_status == "done",
        )
    )
    games = result.scalars().all()

    if time_category:
        games = [g for g in games if classify_time_control(g.time_control) == time_category]

    if not games:
        return {"opening": None, "middlegame": None, "endgame": None, "games_analyzed": 0}

    game_ids = [g.id for g in games]
    summary_result = await db.execute(
        select(GameSummary).where(GameSummary.game_id.in_(game_ids))
    )
    summaries = summary_result.scalars().all()

    phase_totals: dict[str, list[float]] = {"opening": [], "middlegame": [], "endgame": []}
    for s in summaries:
        for phase in ("opening", "middlegame", "endgame"):
            if s.phase_scores and phase in s.phase_scores:
                phase_totals[phase].append(s.phase_scores[phase])

    return {
        phase: round(sum(vals) / len(vals), 1) if vals else None
        for phase, vals in phase_totals.items()
    } | {"games_analyzed": len(summaries)}
