from unittest.mock import AsyncMock, patch

from app.auth.dependencies import set_session


async def test_me_unauthenticated(client):
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_me_authenticated(client, app):
    """Test /auth/me with a valid session."""
    from app.database import get_db
    from app.models.user import User
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from app.models import Base
    from app.config import settings
    import uuid

    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with session_factory() as db:
        user = User(username="testplayer")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = user.id

    session_id = "test-session-123"
    set_session(session_id, user_id)

    response = await client.get(
        "/auth/me",
        cookies={"chesspa_session": session_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testplayer"
    assert data["id"] == str(user_id)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    app.dependency_overrides.clear()


async def test_lichess_login_redirects(client):
    response = await client.get("/auth/lichess/login", follow_redirects=False)
    assert response.status_code == 307
    assert "lichess.org/oauth" in response.headers["location"]


async def test_logout(client):
    import uuid
    from app.auth.dependencies import _sessions

    session_id = "logout-test"
    user_id = uuid.uuid4()
    set_session(session_id, user_id)
    assert session_id in _sessions

    response = await client.post("/auth/logout", cookies={"chesspa_session": session_id})
    assert response.status_code == 200
    assert session_id not in _sessions
