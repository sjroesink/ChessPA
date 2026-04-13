import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

SESSION_COOKIE = "chesspa_session"


async def get_or_create_user(db: AsyncSession, lichess_username: str) -> User:
    result = await db.execute(
        select(User).where(User.username == lichess_username)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(username=lichess_username)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(last_login=datetime.now(timezone.utc))
        )
        await db.commit()
    return user
