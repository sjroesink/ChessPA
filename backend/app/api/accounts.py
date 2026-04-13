import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

CHESS_COM_PROFILE_URL = "https://api.chess.com/pub/player/{username}"


class ConnectChessComRequest(BaseModel):
    username: str


@router.post("/connect/chess-com")
async def connect_chess_com(
    body: ConnectChessComRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify username exists on Chess.com
    async with httpx.AsyncClient() as client:
        response = await client.get(
            CHESS_COM_PROFILE_URL.format(username=body.username.lower()),
            headers={"User-Agent": "ChessPA/0.1"},
        )
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Chess.com user not found")
        response.raise_for_status()

    # Check if already linked
    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user.id,
            ConnectedAccount.platform == "chess_com",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.platform_username = body.username.lower()
        await db.commit()
    else:
        account = ConnectedAccount(
            user_id=user.id,
            platform="chess_com",
            platform_username=body.username.lower(),
        )
        db.add(account)
        await db.commit()

    return {"status": "connected", "platform": "chess_com", "username": body.username.lower()}


@router.delete("/{account_id}")
async def disconnect_account(
    account_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid

    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.id == uuid.UUID(account_id),
            ConnectedAccount.user_id == user.id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.platform == "lichess":
        raise HTTPException(status_code=400, detail="Cannot disconnect Lichess account (used for login)")

    await db.delete(account)
    await db.commit()
    return {"status": "disconnected"}


@router.put("/{account_id}/auto-sync")
async def toggle_auto_sync(
    account_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid

    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.id == uuid.UUID(account_id),
            ConnectedAccount.user_id == user.id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    account.auto_sync = not account.auto_sync
    await db.commit()
    return {"auto_sync": account.auto_sync}
