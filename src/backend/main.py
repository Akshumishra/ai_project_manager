from __future__ import annotations

import logging
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Force include root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.backend.config import settings
from src.backend.db.database import create_tables
from src.backend.auth import routes as auth_routes
from src.backend.collaborative_document.routes import document as doc_routes
from src.backend.collaborative_document.routes import block as block_routes
from src.backend.collaborative_document.routes import websocket as ws_routes
from src.backend.collaborative_document.utils.scheduler import start_scheduler
from src.backend.collaborative_document.utils.block_sync_worker import flush_dirty_blocks
from src.backend.requirement_gather import project_routes as requirement_routes
from src.backend.project import routes as project_routes
from src.backend.technical_doc import tech_doc_routes
from src.backend.resume_parsing import routes as resume_routes
from src.backend.task_creator import task_creator_routes
from src.backend.task_assigner.routes.task_assigner_routes import router as task_assigner_router
from src.backend.slack import slack_routes
from src.backend.meeting_bot.api.routers import router as api_router
from src.backend.qa_chatbot.routes import slack_events as merged_slack_events
from src.backend.standups.routes import standup_routes
from src.backend.standups.services.standup_scheduler import standup_scheduler

# Create tables if they don't exist
create_tables()

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Life-cycle manager for background workers and schedulers.
    """
    logger.info("Initializing backend services...")
    
    # 1. Start Collaborative Document scheduler/sync
    for _ in range(5):
        flush_dirty_blocks()
    start_scheduler()
    
    # 2. Start Standup Scheduler
    try:
        standup_scheduler.start()
        logger.info("Daily Standup Scheduler started.")
    except Exception as e:
        logger.error(f"Failed to start Standup Scheduler: {e}")

    yield

    # Shutdown
    logger.info("Shutting down backend services...")
    try:
        standup_scheduler.shutdown()
    except Exception:
        pass

def configure_logging():
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

configure_logging()

app = FastAPI(
    title=settings.APP_TITLE,
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5175",
        "http://127.0.0.1:5175"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Core API Routes ──────────────────────────────────────────────────────────
app.include_router(auth_routes.router)
app.include_router(resume_routes.router)
app.include_router(project_routes.router)
app.include_router(doc_routes.router)
app.include_router(block_routes.router)
app.include_router(ws_routes.router)
app.include_router(slack_routes.router)

# ── Agentic Workflows ────────────────────────────────────────────────────────
app.include_router(requirement_routes.router, prefix="/api/agent")
app.include_router(tech_doc_routes.router, prefix="/api/agent")
app.include_router(task_creator_routes.router)
app.include_router(task_assigner_router)
app.include_router(api_router)

# ── Slack & Standup Features ──────────────────────────────────────────────────
# Unified Slack Request URL: POST /api/slack/events
app.include_router(merged_slack_events.router, tags=["Slack Events"])

# Standup Management API
app.include_router(standup_routes.router)

@app.get("/")
def home():
    return {
        "message": "Welcome to AI-Project Manager API",
        "status": "online",
        "environment": settings.APP_ENVIRONMENT
    }

if __name__ == "__main__":
    uvicorn.run("src.backend.main:app", host="0.0.0.0", port=8000, reload=True)
