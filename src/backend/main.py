import os
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from src.backend.meeting_bot.api.routers import router as api_router
from src.backend.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Modern lifespan handler replacing deprecated on_event decorators.
    """
    logger.info("Calendar Meeting service initialized.")
    yield
    logger.info("Calendar Meeting service shutting down.")


def _get_docs_config() -> dict:
    """Conditionally disable OpenAPI docs in production."""
    if settings.is_production:
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
    app.include_router(api_router)

    return app


# ⚡️ Instantiate the application layout direct scope
app = create_app()


def configure_logging():
    """Set up structured console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    configure_logging()

    print("\n🚀  Starting API server on 127.0.0.1:8000")
    print("    Documentation: http://127.0.0.1:8000/docs\n")

    uvicorn.run(
        "src.backend.main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True
    )


if __name__ == "__main__":
    main()
