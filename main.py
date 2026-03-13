from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.backend.requirement_gather.project_routes import router as project_routes
from src.backend.db.database import engine, Base

# Import all models to ensure they are registered with Base before create_all
import src.backend.model

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(project_routes)

