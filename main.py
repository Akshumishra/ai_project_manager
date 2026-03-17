import uvicorn
from fastapi import FastAPI
from src.backend.qa_chatbot.routes import slack_events
from src.backend.logger import get_logger
from src.backend.config import settings

from contextlib import asynccontextmanager

logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_TITLE}...")
    yield

app = FastAPI(title=settings.APP_TITLE, lifespan=lifespan)

app.include_router(slack_events.router)

@app.get("/")
async def root():
    return {"status": "ok", "service": settings.APP_TITLE}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
