import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.auth.dependencies import set_session


async def test_connect_chess_com(client, app, test_db_factory, override_db):
    async with test_db_factory() as db:
        user = User(username="testplayer")
        db.add(user)
        await db.commit()
        await db.refresh(user)

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


async def test_connect_chess_com_not_found(client, app, test_db_factory, override_db):
    async with test_db_factory() as db:
        user = User(username="testplayer")
        db.add(user)
        await db.commit()
        await db.refresh(user)

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


async def test_toggle_auto_sync(client, app, test_db_factory, override_db):
    async with test_db_factory() as db:
        user = User(username="testplayer")
        db.add(user)
        await db.commit()
        await db.refresh(user)

    async with test_db_factory() as db:
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
