"""FastAPI application entrypoint for the tour itinerary builder."""
from __future__ import annotations

from fastapi import FastAPI

from .api import router as api_router
from .api.deps import get_db
from .database import Base, engine

Base.metadata.create_all(bind=engine)


def create_application() -> FastAPI:
    app = FastAPI(title="Tour Planner API", version="2.0.0")
    app.include_router(api_router)

    @app.get("/", tags=["health"], summary="Service healthcheck")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "message": "Tour Planner API is running"}

    return app


app = create_application()

__all__ = ["app", "create_application", "get_db"]
