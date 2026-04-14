import uuid
from datetime import datetime, timezone

from app.models.user import User
from app.models.game import Game
from app.auth.dependencies import set_session


async def _create_user(factory):
    async with factory() as db:
        user = User(
            username="testplayer",
            auth_provider="google",
            email="games@test.com",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def _create_game(factory, user_id, **overrides):
    defaults = {
        "user_id": user_id,
        "platform": "chess.com",
        "pgn": "1. e4 e5 2. Nf3 Nc6 *",
        "white_username": "testplayer",
        "black_username": "opponent",
        "user_color": "white",
        "result": "win",
        "opening_name": "Italian Game",
        "opening_eco": "C50",
        "time_control": "300+0",
        "user_elo": 1500,
        "opponent_elo": 1480,
        "played_at": datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
        "move_count": 2,
        "import_source": "chess.com",
        "content_hash": uuid.uuid4().hex,
    }
    defaults.update(overrides)

    async with factory() as db:
        game = Game(**defaults)
        db.add(game)
        await db.commit()
        await db.refresh(game)
        return game


async def test_list_games(client, app, test_db_factory, override_db):
    user = await _create_user(test_db_factory)
    game = await _create_game(test_db_factory, user.id)
    set_session("g1", user.id)

    response = await client.get(
        "/api/games",
        cookies={"chesspa_session": "g1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert len(data["games"]) == 1
    assert data["games"][0]["id"] == str(game.id)
    assert data["games"][0]["result"] == "win"
    assert data["games"][0]["time_category"] == "blitz"


async def test_list_games_filter_result(client, app, test_db_factory, override_db):
    user = await _create_user(test_db_factory)
    await _create_game(test_db_factory, user.id, result="win")
    set_session("g2", user.id)

    response = await client.get(
        "/api/games?result=loss",
        cookies={"chesspa_session": "g2"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["games"]) == 0


async def test_game_detail(client, app, test_db_factory, override_db):
    user = await _create_user(test_db_factory)
    game = await _create_game(test_db_factory, user.id)
    set_session("g3", user.id)

    response = await client.get(
        f"/api/games/{game.id}",
        cookies={"chesspa_session": "g3"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(game.id)
    assert data["pgn"] == "1. e4 e5 2. Nf3 Nc6 *"
    assert data["import_source"] == "chess.com"
    assert data["opening_name"] == "Italian Game"


async def test_game_detail_not_found(client, app, test_db_factory, override_db):
    user = await _create_user(test_db_factory)
    set_session("g4", user.id)

    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"/api/games/{fake_id}",
        cookies={"chesspa_session": "g4"},
    )
    assert response.status_code == 404


async def test_list_games_unauthorized(client, app):
    response = await client.get("/api/games")
    assert response.status_code == 401
