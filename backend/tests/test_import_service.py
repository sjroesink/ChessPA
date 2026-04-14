import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.chess_services.import_service import (
    import_chesscom_game,
    import_lichess_game,
    import_pgn_text,
)
from app.config import settings
from app.models import Base
from app.models.user import User

SAMPLE_PGN = """[Event "Live Chess"]
[Site "Chess.com"]
[Date "2024.06.15"]
[White "testplayer"]
[Black "opponent1"]
[Result "1-0"]
[WhiteElo "1500"]
[BlackElo "1400"]
[TimeControl "600"]
[ECO "B20"]
[Opening "Sicilian Defense"]

1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 1-0"""

SAMPLE_CHESSCOM_GAME = {
    "url": "https://www.chess.com/game/live/12345",
    "pgn": SAMPLE_PGN,
    "end_time": 1718467200,
    "time_control": "600",
    "white": {"username": "testplayer", "rating": 1500},
    "black": {"username": "opponent1", "rating": 1400},
}

SAMPLE_LICHESS_GAME = {
    "id": "abc12345",
    "pgn": SAMPLE_PGN,
    "createdAt": 1718467200000,
    "winner": "white",
    "clock": {"initial": 600, "increment": 0},
    "players": {
        "white": {"user": {"name": "testplayer"}, "rating": 1500},
        "black": {"user": {"name": "opponent1"}, "rating": 1400},
    },
    "opening": {"eco": "B20", "name": "Sicilian Defense"},
}


@pytest.fixture
async def db_engine():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
async def test_user(db_session: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        username="test",
        auth_provider="google",
        email=f"test-{uuid.uuid4().hex[:8]}@email.com",
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_import_chesscom_game(db_session: AsyncSession, test_user: User):
    game = await import_chesscom_game(
        db_session, test_user.id, "testplayer", SAMPLE_CHESSCOM_GAME
    )
    await db_session.commit()

    assert game is not None
    assert game.platform == "chess.com"
    assert game.user_color == "white"
    assert game.result == "win"
    assert game.white_username == "testplayer"
    assert game.black_username == "opponent1"
    assert game.user_elo == 1500
    assert game.opponent_elo == 1400
    assert game.import_source == "chess.com"
    assert game.content_hash is not None
    assert game.time_control == "rapid"
    assert game.opening_eco == "B20"


@pytest.mark.asyncio
async def test_import_chesscom_game_as_black(db_session: AsyncSession, test_user: User):
    game = await import_chesscom_game(
        db_session, test_user.id, "opponent1", SAMPLE_CHESSCOM_GAME
    )
    await db_session.commit()

    assert game is not None
    assert game.user_color == "black"
    assert game.result == "loss"
    assert game.user_elo == 1400
    assert game.opponent_elo == 1500


@pytest.mark.asyncio
async def test_import_dedup(db_session: AsyncSession, test_user: User):
    game1 = await import_chesscom_game(
        db_session, test_user.id, "testplayer", SAMPLE_CHESSCOM_GAME
    )
    await db_session.commit()
    assert game1 is not None

    game2 = await import_chesscom_game(
        db_session, test_user.id, "testplayer", SAMPLE_CHESSCOM_GAME
    )
    assert game2 is None


@pytest.mark.asyncio
async def test_import_lichess_game(db_session: AsyncSession, test_user: User):
    game = await import_lichess_game(
        db_session, test_user.id, "testplayer", SAMPLE_LICHESS_GAME
    )
    await db_session.commit()

    assert game is not None
    assert game.platform == "lichess"
    assert game.user_color == "white"
    assert game.result == "win"
    assert game.import_source == "lichess"
    assert game.platform_game_id == "abc12345"
    assert game.time_control == "rapid"


@pytest.mark.asyncio
async def test_import_lichess_draw(db_session: AsyncSession, test_user: User):
    game_data = {**SAMPLE_LICHESS_GAME, "id": "draw123"}
    del game_data["winner"]
    # Modify PGN to be a draw so content_hash differs
    draw_pgn = SAMPLE_PGN.replace("1-0", "1/2-1/2")
    game_data["pgn"] = draw_pgn

    game = await import_lichess_game(
        db_session, test_user.id, "testplayer", game_data
    )
    await db_session.commit()

    assert game is not None
    assert game.result == "draw"


@pytest.mark.asyncio
async def test_import_pgn_text(db_session: AsyncSession, test_user: User):
    multi_pgn = SAMPLE_PGN + "\n\n" + SAMPLE_PGN.replace("opponent1", "opponent2").replace("1-0", "0-1")

    games = await import_pgn_text(db_session, test_user.id, "testplayer", multi_pgn)
    await db_session.commit()

    assert len(games) == 2
    assert games[0].result == "win"
    assert games[1].result == "loss"
    assert games[1].black_username == "opponent2"


@pytest.mark.asyncio
async def test_import_pgn_text_dedup(db_session: AsyncSession, test_user: User):
    games1 = await import_pgn_text(db_session, test_user.id, "testplayer", SAMPLE_PGN)
    await db_session.commit()
    assert len(games1) == 1

    games2 = await import_pgn_text(db_session, test_user.id, "testplayer", SAMPLE_PGN)
    assert len(games2) == 0
