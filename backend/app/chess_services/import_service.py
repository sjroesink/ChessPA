import io
import uuid
from datetime import datetime, timezone

import chess.pgn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.worker.tasks import analyze_game as analyze_game_task
    _celery_available = True
except Exception:
    _celery_available = False

from app.chess_services.pgn_parser import (
    compute_content_hash,
    determine_result,
    parse_pgn,
)
from app.chess_services.time_control import classify_time_control
from app.models.game import Game


async def import_chesscom_game(
    db: AsyncSession,
    user_id: uuid.UUID,
    chess_com_username: str,
    game_data: dict,
) -> Game | None:
    """Import a single Chess.com game. Returns None if duplicate."""
    pgn_text = game_data.get("pgn", "")
    if not pgn_text:
        return None

    parsed = parse_pgn(pgn_text)

    white_user = game_data["white"]["username"]
    black_user = game_data["black"]["username"]
    is_white = white_user.lower() == chess_com_username.lower()
    user_color = "white" if is_white else "black"

    result = determine_result(parsed["result_raw"], is_white)

    content_hash = compute_content_hash(
        pgn_text,
        str(parsed["played_at"]),
        parsed["white_username"],
        parsed["black_username"],
    )

    existing = await db.execute(
        select(Game).where(Game.content_hash == content_hash)
    )
    if existing.scalar_one_or_none() is not None:
        return None

    user_elo = parsed["white_elo"] if is_white else parsed["black_elo"]
    opponent_elo = parsed["black_elo"] if is_white else parsed["white_elo"]

    time_control_raw = parsed.get("time_control") or game_data.get("time_control")
    time_control_class = classify_time_control(time_control_raw)

    # Use end_time from game_data if available
    played_at = parsed["played_at"]
    if "end_time" in game_data:
        played_at = datetime.fromtimestamp(game_data["end_time"], tz=timezone.utc)

    game = Game(
        user_id=user_id,
        platform="chess.com",
        platform_game_id=game_data.get("url"),
        pgn=parsed["pgn"],
        white_username=white_user,
        black_username=black_user,
        user_color=user_color,
        result=result,
        opening_name=parsed.get("opening_name"),
        opening_eco=parsed.get("opening_eco"),
        time_control=time_control_class,
        user_elo=user_elo,
        opponent_elo=opponent_elo,
        played_at=played_at,
        move_count=parsed["move_count"],
        import_source="chess.com",
        content_hash=content_hash,
    )
    db.add(game)
    await db.flush()
    if _celery_available:
        try:
            analyze_game_task.delay(str(game.id))
        except Exception:
            pass  # Don't fail import if Celery/Redis is down
    return game


async def import_lichess_game(
    db: AsyncSession,
    user_id: uuid.UUID,
    lichess_username: str,
    game_data: dict,
) -> Game | None:
    """Import a single Lichess game. Returns None if duplicate."""
    pgn_text = game_data.get("pgn", "")
    if not pgn_text:
        return None

    parsed = parse_pgn(pgn_text)

    players = game_data.get("players", {})
    white_name = players.get("white", {}).get("user", {}).get("name", "?")
    black_name = players.get("black", {}).get("user", {}).get("name", "?")
    is_white = white_name.lower() == lichess_username.lower()
    user_color = "white" if is_white else "black"

    # Lichess provides winner field: "white", "black", or absent (draw)
    winner = game_data.get("winner")
    if winner is None:
        result = "draw"
    elif (winner == "white" and is_white) or (winner == "black" and not is_white):
        result = "win"
    else:
        result = "loss"

    content_hash = compute_content_hash(
        pgn_text,
        str(parsed["played_at"]),
        parsed["white_username"],
        parsed["black_username"],
    )

    existing = await db.execute(
        select(Game).where(Game.content_hash == content_hash)
    )
    if existing.scalar_one_or_none() is not None:
        return None

    # Elo from players dict
    user_side = "white" if is_white else "black"
    opp_side = "black" if is_white else "white"
    user_elo = players.get(user_side, {}).get("rating")
    opponent_elo = players.get(opp_side, {}).get("rating")

    # Time control from clock field
    clock = game_data.get("clock", {})
    if clock:
        initial = clock.get("initial", 0)
        increment = clock.get("increment", 0)
        tc_str = f"{initial}+{increment}" if increment else str(initial)
    else:
        tc_str = parsed.get("time_control")
    time_control_class = classify_time_control(tc_str)

    # Lichess createdAt is in milliseconds
    played_at = parsed["played_at"]
    if "createdAt" in game_data:
        played_at = datetime.fromtimestamp(
            game_data["createdAt"] / 1000, tz=timezone.utc
        )

    game = Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=game_data.get("id"),
        pgn=parsed["pgn"],
        white_username=white_name,
        black_username=black_name,
        user_color=user_color,
        result=result,
        opening_name=parsed.get("opening_name") or game_data.get("opening", {}).get("name"),
        opening_eco=parsed.get("opening_eco") or game_data.get("opening", {}).get("eco"),
        time_control=time_control_class,
        user_elo=user_elo,
        opponent_elo=opponent_elo,
        played_at=played_at,
        move_count=parsed["move_count"],
        import_source="lichess",
        content_hash=content_hash,
    )
    db.add(game)
    await db.flush()
    if _celery_available:
        try:
            analyze_game_task.delay(str(game.id))
        except Exception:
            pass  # Don't fail import if Celery/Redis is down
    return game


async def import_pgn_text(
    db: AsyncSession,
    user_id: uuid.UUID,
    username: str,
    pgn_text: str,
) -> list[Game]:
    """Import multiple games from a PGN text blob. Returns list of imported games."""
    imported: list[Game] = []
    pgn_io = io.StringIO(pgn_text)

    while True:
        game_obj = chess.pgn.read_game(pgn_io)
        if game_obj is None:
            break

        # Reconstruct single-game PGN text
        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
        single_pgn = game_obj.accept(exporter)

        parsed = parse_pgn(single_pgn)

        white_user = parsed["white_username"]
        black_user = parsed["black_username"]
        is_white = white_user.lower() == username.lower()
        user_color = "white" if is_white else "black"

        result = determine_result(parsed["result_raw"], is_white)

        content_hash = compute_content_hash(
            single_pgn,
            str(parsed["played_at"]),
            white_user,
            black_user,
        )

        existing = await db.execute(
            select(Game).where(Game.content_hash == content_hash)
        )
        if existing.scalar_one_or_none() is not None:
            continue

        user_elo = parsed["white_elo"] if is_white else parsed["black_elo"]
        opponent_elo = parsed["black_elo"] if is_white else parsed["white_elo"]
        time_control_class = classify_time_control(parsed.get("time_control"))

        game = Game(
            user_id=user_id,
            platform="pgn_upload",
            platform_game_id=None,
            pgn=parsed["pgn"],
            white_username=white_user,
            black_username=black_user,
            user_color=user_color,
            result=result,
            opening_name=parsed.get("opening_name"),
            opening_eco=parsed.get("opening_eco"),
            time_control=time_control_class,
            user_elo=user_elo,
            opponent_elo=opponent_elo,
            played_at=parsed["played_at"],
            move_count=parsed["move_count"],
            import_source="pgn_upload",
            content_hash=content_hash,
        )
        db.add(game)
        await db.flush()
        if _celery_available:
            try:
                analyze_game_task.delay(str(game.id))
            except Exception:
                pass  # Don't fail import if Celery/Redis is down
        imported.append(game)

    return imported
