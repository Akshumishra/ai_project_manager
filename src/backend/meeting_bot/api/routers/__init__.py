from fastapi import APIRouter
from .sessions import router as sessions_router
from .webhooks import router as webhooks_router
from .slack import router as slack_router

router = APIRouter()
router.include_router(sessions_router)
router.include_router(webhooks_router)
router.include_router(slack_router)
