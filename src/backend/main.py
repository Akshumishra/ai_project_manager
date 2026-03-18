import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.backend.slack.routes import slack_events
from src.backend.standups.routes import standup_routes
from src.backend.standups.services.standup_scheduler import standup_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    standup_scheduler.start()
    yield
    standup_scheduler.shutdown()

app = FastAPI(title="AI Project Manager - StandUp Agent", lifespan=lifespan)

app.include_router(slack_events.router, prefix="/api", tags=["Slack"])
app.include_router(standup_routes.router, prefix="/api", tags=["StandUp"])

@app.get("/")
async def root():
    return {"message": "StandUp Agent API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
