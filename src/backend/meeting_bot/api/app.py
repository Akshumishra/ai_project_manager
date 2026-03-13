from __future__ import annotations

import logging
from fastapi import FastAPI
from meeting_bot.api.routes import router, shutdown_orchestrator

# Setup logging for the API package
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Google Meet Bot API",
        description="API to manage multiple Google Meet recording sessions.",
        version="1.1.0",
    )

    # Include routers
    app.include_router(router)

    @app.on_event("shutdown")
    async def on_shutdown():
        await shutdown_orchestrator()

    return app


app = create_app()
