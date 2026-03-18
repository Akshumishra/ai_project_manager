import sys
import os

# Add the project root to sys.path to resolve 'src' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.backend.routes import slack_events, standup_routes
from src.backend.services.standup_scheduler import standup_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the scheduler on app startup
    standup_scheduler.start()
    yield
    # Clean up on shutdown
    standup_scheduler.shutdown()

app = FastAPI(title="AI Project Manager - StandUp Agent", lifespan=lifespan)

# Include the standup routes with /api prefix to match Slack configuration
app.include_router(slack_events.router, prefix="/api", tags=["Slack"])
app.include_router(standup_routes.router, prefix="/api", tags=["StandUp"])

@app.get("/")
async def root():
    return {"message": "StandUp Agent API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
