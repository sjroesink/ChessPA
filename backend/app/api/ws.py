"""WebSocket endpoint for live, progressive per-ply analysis.

Client connects to /ws/games/{game_id}/analysis (cookie-authed).

Server → client messages:
    {"type": "hello", "total_plies": int, "stages": [stage_names]}
    {"type": "ply", "ply": int, "stage": str, "data": {...}}
    {"type": "stage_progress", "stage": str, "completed": int, "total": int}
    {"type": "done"}
    {"type": "error", "message": str}

Client → server messages:
    {"type": "focus", "ply": int}
    {"type": "request_deep_all"}
    {"type": "cancel_deep_all"}
"""

from __future__ import annotations

import asyncio
import logging
import uuid

import redis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.analysis.pipeline import AnalysisSession
from app.config import settings
from app.database import get_db
from app.models.game import Game
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

_redis = redis.from_url(settings.redis_url, decode_responses=True)


async def _resolve_user(chesspa_session: str | None, db) -> User | None:
    if not chesspa_session:
        return None
    user_id_str = _redis.get(f"session:{chesspa_session}")
    if not user_id_str:
        return None
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


@router.websocket("/ws/games/{game_id}/analysis")
async def ws_game_analysis(websocket: WebSocket, game_id: str):
    await websocket.accept()
    try:
        session_cookie = websocket.cookies.get("chesspa_session")
        async for db in get_db():
            user = await _resolve_user(session_cookie, db)
            if user is None:
                await websocket.send_json({"type": "error", "message": "unauthorized"})
                await websocket.close(code=1008)
                return

            try:
                gid = uuid.UUID(game_id)
            except ValueError:
                await websocket.send_json({"type": "error", "message": "bad_game_id"})
                await websocket.close(code=1008)
                return

            result = await db.execute(
                select(Game).where(Game.id == gid, Game.user_id == user.id)
            )
            game = result.scalar_one_or_none()
            if game is None:
                await websocket.send_json({"type": "error", "message": "not_found"})
                await websocket.close(code=1008)
                return

            stop_event = asyncio.Event()
            send_lock = asyncio.Lock()

            # Signal to Celery background tasks that this game is being watched live.
            focus_key = f"analysis:focus:{game_id}"
            _redis.set(focus_key, "1", ex=3600)

            async def emit(event: dict) -> None:
                async with send_lock:
                    try:
                        await websocket.send_json(event)
                    except Exception:
                        stop_event.set()

            session = AnalysisSession(db=db, game=game, emitter=emit)
            await session.load()

            await emit(
                {
                    "type": "hello",
                    "total_plies": session.total_plies(),
                    "stages": ["shallow", "standard", "deep", "enrich"],
                }
            )

            async def receiver() -> None:
                try:
                    while True:
                        msg = await websocket.receive_json()
                        t = msg.get("type")
                        if t == "focus":
                            ply = int(msg.get("ply", -1))
                            if ply >= 0:
                                session.set_focus(ply)
                        elif t == "request_deep_all":
                            session.set_deep_all(True)
                        elif t == "cancel_deep_all":
                            session.set_deep_all(False)
                        elif t == "close":
                            stop_event.set()
                            return
                except WebSocketDisconnect:
                    stop_event.set()
                except Exception as exc:  # pragma: no cover
                    logger.warning("ws receiver error: %s", exc)
                    stop_event.set()

            recv_task = asyncio.create_task(receiver())
            try:
                await session.run(stop_event=stop_event)
                await emit({"type": "done"})
            finally:
                stop_event.set()
                recv_task.cancel()
                try:
                    await recv_task
                except (asyncio.CancelledError, Exception):
                    pass
                try:
                    _redis.delete(focus_key)
                except Exception:
                    pass
            return
    except WebSocketDisconnect:
        return
    except Exception as exc:  # pragma: no cover
        logger.exception("ws handler crashed: %s", exc)
        try:
            await websocket.send_json({"type": "error", "message": "server_error"})
        finally:
            await websocket.close(code=1011)
