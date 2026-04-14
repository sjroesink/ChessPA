import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings
from app.database import get_db
from app.models import Base
from app.models.user import User
from app.models.game import Game
from app.models.move_analysis import MoveAnalysis
from app.models.game_summary import GameSummary
from app.auth.dependencies import set_session


async def _setup(app):
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override():
        async with factory() as s:
            yield s
    app.dependency_overrides[get_db] = override

    async with factory() as db:
        user = User(username="analyst", auth_provider="google", email="analysis@test.com")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        game = Game(
            user_id=user.id, platform="chess_com", pgn="1. e4 e5 1-0",
            white_username="analyst", black_username="opponent",
            user_color="white", result="win", time_control="600",
            played_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
            move_count=2, import_source="sync",
            content_hash="analysis-test-hash", analysis_status="done",
        )
        db.add(game)
        await db.commit()
        await db.refresh(game)

        ma = MoveAnalysis(
            game_id=game.id, move_number=1, color="white", move_san="e4",
            eval_before=0.0, eval_after=20.0, best_move_san="e4", classification="best",
        )
        db.add(ma)

        gs = GameSummary(
            game_id=game.id, blunders=0, mistakes=0, inaccuracies=0,
            avg_eval_loss=5.0,
            phase_scores={"opening": 95, "middlegame": 90, "endgame": 85},
            time_trouble=False,
        )
        db.add(gs)
        await db.commit()

    set_session("analysis-test", user.id)
    return engine, user, game


async def _cleanup(engine, app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    app.dependency_overrides.clear()


async def test_get_analysis(client, app):
    engine, user, game = await _setup(app)
    response = await client.get(
        f"/api/games/{game.id}/analysis",
        cookies={"chesspa_session": "analysis-test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["blunders"] == 0
    assert data["summary"]["avg_eval_loss"] == 5.0
    assert len(data["moves"]) == 1
    assert data["moves"][0]["move_san"] == "e4"
    await _cleanup(engine, app)


async def test_get_analysis_not_found(client, app):
    engine, user, game = await _setup(app)
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"/api/games/{fake_id}/analysis",
        cookies={"chesspa_session": "analysis-test"},
    )
    assert response.status_code == 404
    await _cleanup(engine, app)
