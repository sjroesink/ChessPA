from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

SESSION_COOKIE = "chesspa_session"


async def get_or_create_user_by_email(
    db: AsyncSession, email: str, username: str, auth_provider: str
) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(username=username, email=email, auth_provider=auth_provider)
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


async def get_or_create_user_by_username(
    db: AsyncSession, username: str, auth_provider: str
) -> User:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(username=username, auth_provider=auth_provider)
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
