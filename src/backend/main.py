import sys
import os

# Add the project root to sys.path to resolve 'src' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import FastAPI
from src.backend.routes import slack_events, standup_routes

app = FastAPI(title="AI Project Manager - StandUp Agent")

# Include the standup routes
app.include_router(slack_events.router, tags=["Slack"])
app.include_router(standup_routes.router, tags=["StandUp"])

@app.get("/")
async def root():
    return {"message": "StandUp Agent API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
