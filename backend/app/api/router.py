from fastapi import APIRouter

from app.api.accounts import router as accounts_router
from app.api.games import router as games_router
from app.api.analysis import router as analysis_router
from app.api.stats import router as stats_router
from app.api.coaching import router as coaching_router

router = APIRouter()
router.include_router(accounts_router)
router.include_router(games_router)
router.include_router(analysis_router)
router.include_router(stats_router)
router.include_router(coaching_router)
