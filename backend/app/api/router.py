from fastapi import APIRouter

from app.api.accounts import router as accounts_router
from app.api.games import router as games_router

router = APIRouter()
router.include_router(accounts_router)
router.include_router(games_router)
