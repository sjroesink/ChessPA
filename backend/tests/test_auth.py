import uuid
from unittest.mock import AsyncMock, patch

from app.auth.dependencies import set_session, _sessions
from app.models.user import User


async def test_me_unauthenticated(client):
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_me_authenticated(client, app, test_db_factory, override_db):
    """Test /auth/me with a valid session."""
    async with test_db_factory() as db:
        user = User(username="testplayer", auth_provider="google", email="test@example.com")
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
    assert data["email"] == "test@example.com"
    assert data["auth_provider"] == "google"


async def test_lichess_login_redirects(client):
    response = await client.get("/auth/lichess/login", follow_redirects=False)
    assert response.status_code == 307
    assert "lichess.org/oauth" in response.headers["location"]


async def test_google_login_redirects(client):
    response = await client.get("/auth/google/login", follow_redirects=False)
    assert response.status_code == 307
    assert "accounts.google.com" in response.headers["location"]


async def test_logout(client):
    session_id = "logout-test"
    user_id = uuid.uuid4()
    set_session(session_id, user_id)
    assert session_id in _sessions

    response = await client.post("/auth/logout", cookies={"chesspa_session": session_id})
    assert response.status_code == 200
    assert session_id not in _sessions
