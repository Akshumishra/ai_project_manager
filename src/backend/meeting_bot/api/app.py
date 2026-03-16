from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from meeting_bot.api.routers import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Modern lifespan handler replacing deprecated on_event decorators.

    Startup logic runs before ``yield``; shutdown logic runs after.
    """
    logger.info("Calendar Meeting service initialized.")
    yield
    logger.info("Calendar Meeting service shutting down.")


def _get_docs_config() -> dict:
    """Conditionally disable OpenAPI docs in production."""
    import os
    if os.environ.get("APP_ENVIRONMENT") == "production":
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {}


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Google Meet Bot API",
        description="API to manage multiple Google Meet recording sessions.",
        version="2.0.0",
        lifespan=lifespan,
        **_get_docs_config(),
    )

    # ── CORS ────────────────────────────────────────────────────────────────
    import os
    allowed_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

    # ── Security Headers Middleware ──────────────────────────────────────────
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next) -> Response:
        """Inject standard security headers on every response."""
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    # ── Routers ──────────────────────────────────────────────────────────────
    app.include_router(router)

    return app


app = create_app()
