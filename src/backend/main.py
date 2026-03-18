import uvicorn
import sys
import os
from fastapi import FastAPI

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from fastapi.middleware.cors import CORSMiddleware
from src.backend.qa_chatbot.routes import slack_events
from src.backend.logger import get_logger
from src.backend.config import settings

from contextlib import asynccontextmanager


from src.backend.db.database import engine, Base
from src.backend.auth import routes as auth_routes
from src.backend.collaborative_document.routes import document as doc_routes
from src.backend.collaborative_document.routes import block as block_routes
from src.backend.collaborative_document.routes import websocket as ws_routes
from src.backend.collaborative_document.utils.scheduler import start_scheduler
from src.backend.collaborative_document.utils.block_sync_worker import (
    flush_dirty_blocks,
)
from src.backend.requirement_gather.project_routes import router as project_routes
from src.backend.config import settings
import src.backend.model

logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_TITLE}...")
    yield

app = FastAPI(title=settings.APP_TITLE, lifespan=lifespan)

app.include_router(slack_events.router)

@app.get("/")
async def root():
    return {"status": "ok", "service": settings.APP_TITLE, "message": "Welcome to AI-Project Manager API"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(project_routes)
app.include_router(doc_routes.router)
app.include_router(block_routes.router)
app.include_router(ws_routes.router)
app.include_router(auth_routes.router)


if __name__ == "__main__":
    uvicorn.run("src.backend.main:app", host="0.0.0.0", port=8000, reload=True)
