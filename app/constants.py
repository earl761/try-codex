"""Application-wide constants and defaults."""
from __future__ import annotations

APP_NAME = "Tour Planner"

DEFAULT_LANDING_PAGE: dict[str, object] = {
    "headline": "Build unforgettable journeys with confidence",
    "subheadline": "Streamline itineraries, finances, and supplier management in one dashboard.",
    "call_to_action": "Start planning now",
    "seo_description": "Tour itinerary builder software for travel agencies with CRM, finance, and supplier marketplace.",
    "hero_image_url": "https://example.com/hero.jpg",
    "meta_keywords": ["tour planner", "travel agency software", "itinerary builder"],
}

LANDING_PAGE_TEXT_FIELDS: tuple[str, ...] = (
    "headline",
    "subheadline",
    "call_to_action",
    "seo_description",
    "hero_image_url",
)

DEFAULT_POWERED_BY_LABEL = f"Powered by {APP_NAME}"
