import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Core / Database / Auth / Docs ───────────────────────────────────────────
from src.backend.db.database import create_tables, Base
from src.backend.auth import routes as auth_routes
from src.backend.collaborative_document.routes import document as doc_routes
from src.backend.collaborative_document.routes import block as block_routes
from src.backend.collaborative_document.routes import websocket as ws_routes
from src.backend.collaborative_document.utils.scheduler import start_scheduler
from src.backend.collaborative_document.utils.block_sync_worker import flush_dirty_blocks

from src.backend.project import routes as project_routes
from src.backend.resume_parsing import routes as resume_routes

# ── Meeting Bot ──────────────────────────────────────────────────────────────
from src.backend.meeting_bot.api.routers import router as api_router
from src.backend.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles background workers and schedulers initial triggers seamlessly.
    """
    for _ in range(5):
        flush_dirty_blocks()
    start_scheduler()
    yield

create_tables()
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Include Routers ──────────────────────────────────────────────────────
try:
    app.include_router(project_routes.router)
except AttributeError:
    app.include_router(project_routes)

app.include_router(doc_routes.router)
app.include_router(block_routes.router)
app.include_router(ws_routes.router)
app.include_router(auth_routes.router)
app.include_router(resume_routes.router)
app.include_router(api_router)


@app.get("/")
def home():
    return {"message": "Welcome to AI-Project Manager API"}


if __name__ == "__main__":
    uvicorn.run("src.backend.main:app", host="0.0.0.0", port=8000, reload=True)
