import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.chess_services.import_service import (
    import_chesscom_game,
    import_lichess_game,
    import_pgn_text,
)
from app.chess_services.time_control import classify_time_control
from app.database import get_db
from app.models.connected_account import ConnectedAccount
from app.models.game import Game
from app.models.game_summary import GameSummary
from app.models.user import User

router = APIRouter(prefix="/api/games", tags=["games"])


def _game_to_dict(game: Game) -> dict:
    return {
        "id": str(game.id),
        "platform": game.platform,
        "white_username": game.white_username,
        "black_username": game.black_username,
        "user_color": game.user_color,
        "result": game.result,
        "opening_name": game.opening_name,
        "opening_eco": game.opening_eco,
        "time_control": game.time_control,
        "time_category": classify_time_control(game.time_control),
        "user_elo": game.user_elo,
        "opponent_elo": game.opponent_elo,
        "played_at": game.played_at.isoformat() if game.played_at else None,
        "move_count": game.move_count,
        "analysis_status": game.analysis_status,
    }


def _game_detail_dict(game: Game) -> dict:
    d = _game_to_dict(game)
    d["pgn"] = game.pgn
    d["import_source"] = game.import_source
    return d


@router.get("")
async def list_games(
    platform: str | None = None,
    result: str | None = None,
    opening: str | None = None,
    time_category: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base = select(Game).where(Game.user_id == user.id)

    if platform:
        base = base.where(Game.platform == platform)
    if result:
        base = base.where(Game.result == result)
    if opening:
        base = base.where(Game.opening_name.ilike(f"%{opening}%"))
    if time_category:
        base = base.where(Game.time_control == time_category)
    if since:
        base = base.where(Game.played_at >= since)
    if until:
        base = base.where(Game.played_at <= until)

    # Total count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginated results
    offset = (page - 1) * limit
    query = base.order_by(Game.played_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(query)).scalars().all()

    # Fetch accompanying summaries for the page in one query.
    game_ids = [g.id for g in rows]
    accuracy_map: dict[uuid.UUID, float | None] = {}
    if game_ids:
        summary_rows = (
            await db.execute(select(GameSummary).where(GameSummary.game_id.in_(game_ids)))
        ).scalars().all()
        summaries_by_game = {s.game_id: s for s in summary_rows}
        for g in rows:
            s = summaries_by_game.get(g.id)
            if s is None:
                accuracy_map[g.id] = None
                continue
            accuracy_map[g.id] = (
                s.accuracy_white if g.user_color == "white" else s.accuracy_black
            )

    def _with_accuracy(g: Game) -> dict:
        d = _game_to_dict(g)
        d["accuracy"] = accuracy_map.get(g.id)
        return d

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "games": [_with_accuracy(g) for g in rows],
    }


@router.get("/{game_id}")
async def game_detail(
    game_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        gid = uuid.UUID(game_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid game ID")

    result = await db.execute(
        select(Game).where(Game.id == gid, Game.user_id == user.id)
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    return _game_detail_dict(game)


@router.post("/sync")
async def sync_games(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Reload user with connected accounts eagerly loaded
    result = await db.execute(
        select(User)
        .options(selectinload(User.connected_accounts))
        .where(User.id == user.id)
    )
    user_with_accounts = result.scalar_one()

    imported = 0
    errors: list[str] = []

    for account in user_with_accounts.connected_accounts:
        try:
            if account.platform == "chess_com":
                from app.chess_services.chesscom import fetch_recent_games as fetch_chesscom

                games_data = await fetch_chesscom(account.platform_username)
                for game_data in games_data:
                    game = await import_chesscom_game(
                        db, user.id, account.platform_username, game_data
                    )
                    if game is not None:
                        imported += 1

            elif account.platform == "lichess":
                from app.chess_services.lichess_client import fetch_recent_games as fetch_lichess

                token = None  # OAuth token would be decrypted here
                games_data = await fetch_lichess(account.platform_username, token=token)
                for game_data in games_data:
                    game = await import_lichess_game(
                        db, user.id, account.platform_username, game_data
                    )
                    if game is not None:
                        imported += 1

        except Exception as e:
            errors.append(f"{account.platform}/{account.platform_username}: {e}")

    await db.commit()
    return {"imported": imported, "errors": errors}


@router.post("/import/pgn")
async def import_pgn(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    try:
        pgn_text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    games = await import_pgn_text(db, user.id, user.username, pgn_text)
    await db.commit()

    return {
        "imported": len(games),
        "game_ids": [str(g.id) for g in games],
    }


@router.post("/analyze-all")
async def analyze_all_games(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue Stockfish analysis for all unanalyzed games."""
    result = await db.execute(
        select(Game).where(
            Game.user_id == user.id,
            Game.analysis_status == "pending",
        )
    )
    games = result.scalars().all()

    queued = 0
    for game in games:
        try:
            from app.worker.tasks import analyze_game
            analyze_game.delay(str(game.id))
            queued += 1
        except Exception:
            pass

    return {"queued": queued, "total_pending": len(games)}
