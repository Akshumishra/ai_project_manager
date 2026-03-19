from fastapi import APIRouter
from src.backend.meeting_bot.api.routers.sessions import router as sessions_router
from src.backend.meeting_bot.api.routers.webhooks import router as webhooks_router
from src.backend.meeting_bot.api.routers.slack import router as slack_router

router = APIRouter()
router.include_router(sessions_router)
router.include_router(webhooks_router)
router.include_router(slack_router)
