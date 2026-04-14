import uuid

import redis
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User

SESSION_TTL_SEC = 60 * 60 * 24 * 30  # 30 days
_SESSION_PREFIX = "session:"

_redis = redis.from_url(settings.redis_url, decode_responses=True)


def set_session(session_id: str, user_id: uuid.UUID) -> None:
    _redis.setex(_SESSION_PREFIX + session_id, SESSION_TTL_SEC, str(user_id))


def clear_session(session_id: str) -> None:
    _redis.delete(_SESSION_PREFIX + session_id)


async def get_current_user(
    chesspa_session: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if chesspa_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user_id_str = _redis.get(_SESSION_PREFIX + chesspa_session)
    if user_id_str is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    # Refresh TTL on access
    _redis.expire(_SESSION_PREFIX + chesspa_session, SESSION_TTL_SEC)

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user
