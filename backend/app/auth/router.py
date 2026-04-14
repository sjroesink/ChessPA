import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.auth.lichess import (
    generate_pkce,
    get_authorize_url as lichess_authorize_url,
    exchange_code as lichess_exchange_code,
    get_lichess_user,
)
from app.auth.google import (
    get_authorize_url as google_authorize_url,
    exchange_code as google_exchange_code,
    get_google_user,
)
from app.auth.session import (
    get_or_create_user_by_email,
    get_or_create_user_by_username,
    SESSION_COOKIE,
)
from app.auth.dependencies import get_current_user, set_session, clear_session

router = APIRouter(prefix="/auth", tags=["auth"])

# Temporary state stores
_oauth_states: dict[str, str] = {}  # state -> code_verifier (Lichess)
_google_states: set[str] = set()  # state tokens (Google)


def _create_session_response(user_id, redirect_url: str) -> RedirectResponse:
    session_id = secrets.token_urlsafe(32)
    set_session(session_id, user_id)
    response = RedirectResponse(redirect_url)
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


# --- Google OAuth ---


@router.get("/google/login")
async def google_login():
    state = secrets.token_urlsafe(32)
    _google_states.add(state)
    url = google_authorize_url(state)
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    if state not in _google_states:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    _google_states.discard(state)

    token = await google_exchange_code(code)
    google_data = await get_google_user(token)
    email = google_data["email"]
    name = google_data.get("name", email.split("@")[0])

    user = await get_or_create_user_by_email(db, email, name, "google")
    return _create_session_response(user.id, settings.frontend_url)


# --- Lichess OAuth ---


@router.get("/lichess/login")
async def lichess_login():
    state = secrets.token_urlsafe(32)
    verifier, challenge = generate_pkce()
    _oauth_states[state] = verifier
    url = lichess_authorize_url(state, challenge)
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

    token = await lichess_exchange_code(code, verifier)
    lichess_data = await get_lichess_user(token)
    username = lichess_data["username"]

    user = await get_or_create_user_by_username(db, username, "lichess")

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

    return _create_session_response(user.id, settings.frontend_url)


# --- Common ---


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
        "email": user.email,
        "auth_provider": user.auth_provider,
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
