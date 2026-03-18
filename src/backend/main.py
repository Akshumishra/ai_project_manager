<<<<<<< HEAD
import logging
=======
from contextlib import asynccontextmanager
from fastapi import FastAPI
>>>>>>> af8dd30d58119a11f2c37c2545e22d54abe63d01
import uvicorn

<<<<<<< HEAD
def configure_logging():
    """Set up structured console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def main():
    configure_logging()

    # Import and forward to your FastAPI workspace app
    print("\nStarting API server on 127.0.0.1:8000")
    print("Documentation: http://127.0.0.1:8000/docs\n")
=======
from src.backend.db.database import engine, Base
from src.backend.auth import routes as auth_routes
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

from src.backend.model.user import User
from src.backend.model.project import Project, ProjectMember
from src.backend.model.document import Document, DocumentBlock
from src.backend.model.user_detail import UserDetail

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initial sweep to recover unsaved edits after a crash
    for _ in range(5):
        flush_dirty_blocks()
    
    start_scheduler()
    yield

Base.metadata.create_all(bind=engine)
app = FastAPI(lifespan=lifespan)

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
app.include_router(project_routes.router)
app.include_router(resume_routes.router)



@app.get("/")
def home():
    return {"message": "Welcome to AI-Project Manager API"}
>>>>>>> af8dd30d58119a11f2c37c2545e22d54abe63d01

    # Use string-based reload bind addressing so reload watches your workspace recursively!
    uvicorn.run(
        "src.backend.meeting_bot.api.app:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True
    )

if __name__ == "__main__":
    main()
