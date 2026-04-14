import uuid
from datetime import datetime, timezone

from app.models.user import User
from app.models.game import Game
from app.models.game_summary import GameSummary
from app.auth.dependencies import set_session


async def _create_user(factory):
    async with factory() as db:
        user = User(
            username="statsplayer",
            auth_provider="google",
            email=f"stats-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def _create_game(factory, user_id, **overrides):
    defaults = {
        "user_id": user_id,
        "platform": "chess_com",
        "pgn": "1. e4 e5 *",
        "white_username": "statsplayer",
        "black_username": "opponent",
        "user_color": "white",
        "result": "win",
        "opening_name": "Italian Game",
        "opening_eco": "C50",
        "time_control": "300+0",
        "user_elo": 1500,
        "opponent_elo": 1480,
        "played_at": datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
        "move_count": 2,
        "import_source": "sync",
        "content_hash": uuid.uuid4().hex,
    }
    defaults.update(overrides)

    async with factory() as db:
        game = Game(**defaults)
        db.add(game)
        await db.commit()
        await db.refresh(game)
        return game


async def _create_summary(factory, game_id, **overrides):
    defaults = {
        "game_id": game_id,
        "blunders": 1,
        "mistakes": 2,
        "inaccuracies": 3,
        "avg_eval_loss": 25.0,
        "phase_scores": {"opening": 90.0, "middlegame": 75.0, "endgame": 80.0},
    }
    defaults.update(overrides)

    async with factory() as db:
        summary = GameSummary(**defaults)
        db.add(summary)
        await db.commit()
        await db.refresh(summary)
        return summary


# --- Overview ---

async def test_overview_with_games(client, app, test_db_factory, override_db):
    user = await _create_user(test_db_factory)
    await _create_game(test_db_factory, user.id, result="win", user_elo=1500)
    await _create_game(test_db_factory, user.id, result="loss", user_elo=1480)
    set_session("s1", user.id)

    response = await client.get(
        "/api/stats/overview?days=90",
        cookies={"chesspa_session": "s1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_games"] == 2
    assert data["winrate"] == 50.0
    assert data["current_elo"] is not None
    assert data["avg_accuracy"] is None


async def test_overview_empty(client, app, test_db_factory, override_db):
    user = await _create_user(test_db_factory)
    set_session("s2", user.id)

    response = await client.get(
        "/api/stats/overview?days=30",
        cookies={"chesspa_session": "s2"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_games"] == 0
    assert data["winrate"] == 0


async def test_overview_with_accuracy(client, app, test_db_factory, override_db):
    user = await _create_user(test_db_factory)
    game = await _create_game(test_db_factory, user.id, analysis_status="done")
    await _create_summary(test_db_factory, game.id, avg_eval_loss=20.0)
    set_session("s3", user.id)

    response = await client.get(
        "/api/stats/overview?days=90",
        cookies={"chesspa_session": "s3"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["avg_accuracy"] == 80.0


async def test_overview_unauthorized(client, app):
    response = await client.get("/api/stats/overview")
    assert response.status_code == 401


# --- Openings ---

async def test_openings(client, app, test_db_factory, override_db):
    user = await _create_user(test_db_factory)
    await _create_game(test_db_factory, user.id, opening_name="Italian Game", result="win")
    await _create_game(test_db_factory, user.id, opening_name="Italian Game", result="loss")
    await _create_game(test_db_factory, user.id, opening_name="Sicilian Defense", result="win")
    set_session("s4", user.id)

    response = await client.get(
        "/api/stats/openings?days=90",
        cookies={"chesspa_session": "s4"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["opening"] == "Italian Game"
    assert data[0]["total"] == 2
    assert data[0]["wins"] == 1
    assert data[0]["losses"] == 1
    assert data[0]["winrate"] == 50.0


# --- Elo History ---

async def test_elo_history(client, app, test_db_factory, override_db):
    user = await _create_user(test_db_factory)
    await _create_game(
        test_db_factory, user.id, user_elo=1500,
        played_at=datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc),
    )
    await _create_game(
        test_db_factory, user.id, user_elo=1520,
        played_at=datetime(2026, 4, 2, 10, 0, tzinfo=timezone.utc),
    )
    set_session("s5", user.id)

    response = await client.get(
        "/api/stats/elo-history?days=90",
        cookies={"chesspa_session": "s5"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["elo"] == 1500
    assert data[1]["elo"] == 1520


# --- Phases ---

async def test_phases(client, app, test_db_factory, override_db):
    user = await _create_user(test_db_factory)
    game = await _create_game(test_db_factory, user.id, analysis_status="done")
    await _create_summary(
        test_db_factory, game.id,
        phase_scores={"opening": 90.0, "middlegame": 70.0, "endgame": 85.0},
    )
    set_session("s6", user.id)

    response = await client.get(
        "/api/stats/phases?days=90",
        cookies={"chesspa_session": "s6"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["opening"] == 90.0
    assert data["middlegame"] == 70.0
    assert data["endgame"] == 85.0
    assert data["games_analyzed"] == 1


async def test_phases_empty(client, app, test_db_factory, override_db):
    user = await _create_user(test_db_factory)
    set_session("s7", user.id)

    response = await client.get(
        "/api/stats/phases?days=90",
        cookies={"chesspa_session": "s7"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["opening"] is None
    assert data["games_analyzed"] == 0


# --- Time category filter ---

async def test_overview_time_category_filter(client, app, test_db_factory, override_db):
    user = await _create_user(test_db_factory)
    await _create_game(test_db_factory, user.id, time_control="300+0", result="win")
    await _create_game(test_db_factory, user.id, time_control="900+0", result="loss")
    set_session("s8", user.id)

    response = await client.get(
        "/api/stats/overview?days=90&time_category=blitz",
        cookies={"chesspa_session": "s8"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_games"] == 1
    assert data["winrate"] == 100.0
