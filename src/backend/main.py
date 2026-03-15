from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from src.backend.db.database import engine, Base
from src.backend.collaborative_document.routes import document as doc_routes
from src.backend.collaborative_document.routes import block as block_routes
from src.backend.collaborative_document.routes import websocket as ws_routes
from src.backend.collaborative_document.utils.scheduler import start_scheduler
from src.backend.collaborative_document.utils.block_sync_worker import (
    flush_dirty_blocks,
)

from src.backend.auth import routes as auth_routes
from src.backend.project import routes as project_routes
from src.backend.resume_parsing import routes as resume_routes
from src.backend.requirement_gather import project_routes as requirement_routes
from src.backend.technical_doc import tech_doc_routes as tech_doc_routes
from src.backend.task_creator import task_creator_routes as task_creator_routes
from src.backend.config import Config

Base.metadata.create_all(bind=engine)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(doc_routes.router)
app.include_router(block_routes.router)
app.include_router(ws_routes.router)

app.include_router(auth_routes.router)
app.include_router(project_routes.router)
app.include_router(resume_routes.router)
app.include_router(requirement_routes.router, prefix="/api/agent")
app.include_router(tech_doc_routes.router, prefix="/api/agent")
app.include_router(task_creator_routes.router)


@app.on_event("startup")
def start_worker():
    for _ in range(5):
        flush_dirty_blocks()

    start_scheduler()


@app.get("/")
def home():
    return {"message": "Welcome to AI-Project Manager API"}


if __name__ == "__main__":
    uvicorn.run("src.backend.main:app", host="0.0.0.0", port=8000, reload=True)
