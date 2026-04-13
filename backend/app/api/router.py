from fastapi import APIRouter

from app.api.accounts import router as accounts_router

router = APIRouter()
router.include_router(accounts_router)
