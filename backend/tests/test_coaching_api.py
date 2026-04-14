import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings
from app.database import get_db
from app.models import Base
from app.models.user import User
from app.models.coaching_insight import CoachingInsight
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
        user = User(username="coach_api", auth_provider="google", email="coachapi@test.com")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        insight = CoachingInsight(
            user_id=user.id,
            type="weakness",
            title="Test zwakte",
            description="Je maakt te veel blunders.",
            severity="high",
            related_games=[],
            model_version="test-model",
        )
        db.add(insight)
        await db.commit()
        await db.refresh(insight)

    set_session("coaching-test", user.id)
    return engine, user, insight


async def _cleanup(engine, app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    app.dependency_overrides.clear()


async def test_list_insights(client, app):
    engine, user, insight = await _setup(app)
    response = await client.get("/api/coaching/insights", cookies={"chesspa_session": "coaching-test"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "weakness"
    assert data[0]["title"] == "Test zwakte"
    await _cleanup(engine, app)


async def test_get_insight_detail(client, app):
    engine, user, insight = await _setup(app)
    response = await client.get(
        f"/api/coaching/insights/{insight.id}",
        cookies={"chesspa_session": "coaching-test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Je maakt te veel blunders."
    await _cleanup(engine, app)


async def test_get_insight_not_found(client, app):
    engine, user, insight = await _setup(app)
    fake = str(uuid.uuid4())
    response = await client.get(
        f"/api/coaching/insights/{fake}",
        cookies={"chesspa_session": "coaching-test"},
    )
    assert response.status_code == 404
    await _cleanup(engine, app)
