import secrets
import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.auth.lichess import generate_pkce, get_authorize_url, exchange_code, get_lichess_user
from app.auth.session import get_or_create_user, SESSION_COOKIE
from app.auth.dependencies import get_current_user, set_session, clear_session

router = APIRouter(prefix="/auth", tags=["auth"])

# Temporary state store — maps state to code_verifier
_oauth_states: dict[str, str] = {}


@router.get("/lichess/login")
async def lichess_login():
    state = secrets.token_urlsafe(32)
    verifier, challenge = generate_pkce()
    _oauth_states[state] = verifier
    url = get_authorize_url(state, challenge)
    return RedirectResponse(url)


@router.get("/lichess/callback")
async def lichess_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    verifier = _oauth_states.pop(state, None)
    if verifier is None:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    token = await exchange_code(code, verifier)
    lichess_data = await get_lichess_user(token)
    username = lichess_data["username"]

    user = await get_or_create_user(db, username)

    # Upsert connected account for Lichess
    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user.id,
            ConnectedAccount.platform == "lichess",
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        account = ConnectedAccount(
            user_id=user.id,
            platform="lichess",
            platform_username=username,
        )
        db.add(account)
        await db.commit()

    session_id = secrets.token_urlsafe(32)
    set_session(session_id, user.id)

    response = RedirectResponse(settings.frontend_url)
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


@router.post("/logout")
async def logout(
    response: Response,
    chesspa_session: str | None = Cookie(None),
):
    if chesspa_session:
        clear_session(chesspa_session)
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "ok"}


@router.get("/me")
async def me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.connected_accounts))
    )
    user = result.scalar_one()
    return {
        "id": str(user.id),
        "username": user.username,
        "connected_accounts": [
            {
                "id": str(a.id),
                "platform": a.platform,
                "platform_username": a.platform_username,
                "auto_sync": a.auto_sync,
            }
            for a in user.connected_accounts
        ],
    }
