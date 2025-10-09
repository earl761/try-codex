"""FastAPI application entrypoint for the tour itinerary builder."""
from __future__ import annotations

from datetime import datetime
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import crud, schemas
from .api import router as api_router
from .api.deps import get_db
from .database import Base, engine

Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="app/templates")


def create_application() -> FastAPI:
    app = FastAPI(title="Tour Planner API", version="4.0.0")
    app.include_router(api_router)

    @app.get("/", response_class=HTMLResponse, tags=["marketing"], summary="SEO landing page")
    def landing_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
        content = crud.get_landing_page_content(db)
        packages = [
            schemas.SubscriptionPackage.model_validate(pkg)
            for pkg in crud.list_subscription_packages(db, only_active=True)
        ]

        return templates.TemplateResponse(
            request,
            "landing.html",
            {
                "content": content,
                "packages": packages,
                "current_year": datetime.utcnow().year,
            },
        )

    @app.get("/health", tags=["health"], summary="Service healthcheck")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "message": "Tour Planner API is running"}

    return app


app = create_application()

__all__ = ["app", "create_application", "get_db"]
