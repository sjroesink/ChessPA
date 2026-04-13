import uuid

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.auth.session import SESSION_COOKIE

# In-memory session store — replace with Redis in production
_sessions: dict[str, uuid.UUID] = {}


def set_session(session_id: str, user_id: uuid.UUID) -> None:
    _sessions[session_id] = user_id


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


async def get_current_user(
    chesspa_session: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if chesspa_session is None or chesspa_session not in _sessions:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    user_id = _sessions[chesspa_session]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user
