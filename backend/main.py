"""Entry point for the FastAPI application.

This module constructs the FastAPI application, configures CORS
middleware based on environment settings and exposes a simple health
check endpoint. Additional routers will be included in later phases to
implement the full API surface.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title="Toxicology Review Agent")

    # Configure CORS if origins are provided
    origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint returning a simple status message."""
        return {"status": "ok"}

    # Register API routers
    from .routers.sessions import router as sessions_router  # noqa: WPS433
    from .routers.documents import router as documents_router  # noqa: WPS433
    from .routers.pass1 import router as pass1_router  # noqa: WPS433
    from .routers.pass2 import router as pass2_router  # noqa: WPS433
    from .routers.clarifications import router as clarifications_router  # noqa: WPS433
    from .routers.findings import router as findings_router  # noqa: WPS433
    from .routers.dataset import router as dataset_router  # noqa: WPS433
    from .routers.finetune import router as finetune_router  # noqa: WPS433

    app.include_router(sessions_router)
    app.include_router(documents_router)
    app.include_router(pass1_router)
    app.include_router(pass2_router)
    app.include_router(clarifications_router)
    app.include_router(findings_router)
    app.include_router(dataset_router)
    app.include_router(finetune_router)

    return app


app = create_app()