from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.backend.requirement_gather.project_routes import router as project_routes


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

