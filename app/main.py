"""FastAPI application entrypoint for the tour itinerary builder."""
from __future__ import annotations

from datetime import datetime
from typing import Dict

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import crud, schemas
from fastapi import FastAPI

from .api import router as api_router
from .api.deps import get_db
from .database import Base, engine

Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="app/templates")

DEFAULT_LANDING = schemas.LandingPageContent(
    headline="Build unforgettable journeys with confidence",
    subheadline="Streamline itineraries, finances, and supplier management in one dashboard.",
    call_to_action="Start planning now",
    seo_description="Tour itinerary builder software for travel agencies with CRM, finance, and supplier marketplace.",
    hero_image_url="https://example.com/hero.jpg",
    meta_keywords=["tour planner", "travel agency software", "itinerary builder"],
)


def create_application() -> FastAPI:
    app = FastAPI(title="Tour Planner API", version="3.0.0")
    app.include_router(api_router)

    @app.get("/", response_class=HTMLResponse, tags=["marketing"], summary="SEO landing page")
    def landing_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
        settings: Dict[str, str] = {setting.key: setting.value for setting in crud.list_site_settings(db)}
        content = DEFAULT_LANDING.model_copy()
        packages = [
            schemas.SubscriptionPackage.model_validate(pkg)
            for pkg in crud.list_subscription_packages(db, only_active=True)
        ]

        for field in ("headline", "subheadline", "call_to_action", "seo_description", "hero_image_url"):
            if field in settings:
                setattr(content, field, settings[field])

        keywords = settings.get("meta_keywords")
        if keywords:
            content.meta_keywords = [keyword.strip() for keyword in keywords.split(",") if keyword.strip()]

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
            {"content": content, "current_year": datetime.utcnow().year},
        )

    @app.get("/health", tags=["health"], summary="Service healthcheck")

def create_application() -> FastAPI:
    app = FastAPI(title="Tour Planner API", version="2.0.0")
    app.include_router(api_router)

    @app.get("/", tags=["health"], summary="Service healthcheck")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "message": "Tour Planner API is running"}

    return app


app = create_application()

__all__ = ["app", "create_application", "get_db"]
