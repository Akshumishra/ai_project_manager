from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
import os
import logging
from sqlalchemy.orm import configure_mappers
from fastapi.middleware.cors import CORSMiddleware
from src.backend.db.database import Base, create_tables
from src.backend.auth import routes as auth_routes
from src.backend.collaborative_document.routes import document as doc_routes
from src.backend.collaborative_document.routes import block as block_routes
from src.backend.collaborative_document.routes import websocket as ws_routes
from src.backend.collaborative_document.utils.scheduler import start_scheduler
from src.backend.collaborative_document.utils.block_sync_worker import (
    flush_dirty_blocks,
)
from src.backend.requirement_gather import project_routes as requirement_routes
from src.backend.project import routes as project_routes
from src.backend.technical_doc import tech_doc_routes
from src.backend.resume_parsing import routes as resume_routes
from src.backend.task_creator import task_creator_routes
from src.backend.task_assigner.routes.task_assigner_routes import router as task_assigner_router
from src.backend.config import settings
from src.backend.slack import slack_routes

from src.backend.meeting_bot.api.routers import router as api_router
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from src.backend.qa_chatbot.routes import slack_events


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initial sweep to recover unsaved edits after a crash
    print("Starting AI-Project Manager backend...")
    for _ in range(5):
        flush_dirty_blocks()
    
    start_scheduler()
    yield


create_tables()
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Application Routes
app.include_router(auth_routes.router)
app.include_router(resume_routes.router)
app.include_router(project_routes.router)
app.include_router(doc_routes.router)
app.include_router(block_routes.router)
app.include_router(ws_routes.router)
app.include_router(slack_routes.router)

# Agent & Tool Routes
app.include_router(requirement_routes.router, prefix="/api/agent")
app.include_router(tech_doc_routes.router, prefix="/api/agent")
app.include_router(task_creator_routes.router)
app.include_router(task_assigner_router)
app.include_router(api_router)
app.include_router(slack_events.router)

@app.get("/")
def home():
    return {"message": "Welcome to AI-Project Manager API"}


if __name__ == "__main__":
    uvicorn.run("src.backend.main:app", host="0.0.0.0", port=8000, reload=True)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Modern lifespan handler replacing deprecated on_event decorators.
    """
    logger.info("Calendar Meeting service initialized.")
    print("Starting AI-Project Manager backend...")
    for _ in range(5):
        flush_dirty_blocks()
    
    start_scheduler()
    yield
    logger.info("Calendar Meeting service shutting down.")


def _get_docs_config() -> dict:
    """Conditionally disable OpenAPI docs in production."""
    if settings.is_production:
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {}


def configure_logging():
    """Set up structured console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    configure_logging()

    print("\n🚀  Starting API server on 127.0.0.1:8000")
    print("    Documentation: http://127.0.0.1:8000/docs\n")

    uvicorn.run(
        "src.backend.main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True
    )


if __name__ == "__main__":
    main()
