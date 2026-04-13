import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.database import get_db
from app.models import Base
from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.auth.dependencies import set_session, get_current_user


async def _setup_db(app):
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = override
    return engine, factory


async def _create_user(factory, username="testplayer"):
    async with factory() as db:
        user = User(username=username)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def _cleanup(engine, app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    app.dependency_overrides.clear()


async def test_connect_chess_com(client, app):
    engine, factory = await _setup_db(app)
    user = await _create_user(factory)
    set_session("s1", user.id)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch("app.api.accounts.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        response = await client.post(
            "/api/accounts/connect/chess-com",
            json={"username": "TestPlayer"},
            cookies={"chesspa_session": "s1"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "chess_com"
    assert data["username"] == "testplayer"

    await _cleanup(engine, app)


async def test_connect_chess_com_not_found(client, app):
    engine, factory = await _setup_db(app)
    user = await _create_user(factory)
    set_session("s2", user.id)

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("app.api.accounts.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        response = await client.post(
            "/api/accounts/connect/chess-com",
            json={"username": "nonexistent"},
            cookies={"chesspa_session": "s2"},
        )

    assert response.status_code == 404

    await _cleanup(engine, app)


async def test_toggle_auto_sync(client, app):
    engine, factory = await _setup_db(app)
    user = await _create_user(factory)

    async with factory() as db:
        account = ConnectedAccount(
            user_id=user.id,
            platform="chess_com",
            platform_username="testplayer",
            auto_sync=True,
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)
        account_id = str(account.id)

    set_session("s3", user.id)

    response = await client.put(
        f"/api/accounts/{account_id}/auto-sync",
        cookies={"chesspa_session": "s3"},
    )
    assert response.status_code == 200
    assert response.json()["auto_sync"] is False

    await _cleanup(engine, app)
