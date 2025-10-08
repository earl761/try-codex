"""Utility helpers for itinerary formatting and media management."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from random import randint
from typing import Iterable, List, Optional
from uuid import uuid4

from jinja2 import Environment, PackageLoader, select_autoescape
from PIL import Image

from . import models

BASE_DIR = Path(__file__).resolve().parent
MEDIA_ROOT = BASE_DIR / "media_storage"
ORIGINAL_MEDIA_DIR = MEDIA_ROOT / "original"
OPTIMIZED_MEDIA_DIR = MEDIA_ROOT / "optimized"

AVAILABLE_SUPPLIER_INTEGRATIONS: dict[str, List[str]] = {
    "amadeus": ["hotels", "flights"],
    "local_inventories": ["lodges", "transport"],
}


def _ensure_media_directories() -> None:
    for directory in (ORIGINAL_MEDIA_DIR, OPTIMIZED_MEDIA_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def render_itinerary(itinerary: models.Itinerary) -> str:
    """Render an itinerary into a printable text/HTML hybrid document."""
    env = Environment(
        loader=PackageLoader("app", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
        enable_async=False,
    )
    template = env.get_template("itinerary.html")
    return template.render(itinerary=itinerary)


def optimize_image_upload(data: bytes, filename: str) -> dict[str, int | str]:
    """Persist an uploaded image and generate an optimized rendition."""

    if not data:
        raise ValueError("Uploaded file is empty")

    try:
        image = Image.open(BytesIO(data))
    except Exception as exc:  # pragma: no cover - defensive branch
        raise ValueError("Uploaded file is not a valid image") from exc

    image = image.convert("RGB")
    _ensure_media_directories()

    base_name = uuid4().hex
    original_suffix = Path(filename).suffix.lower() or ".jpg"
    original_path = ORIGINAL_MEDIA_DIR / f"{base_name}{original_suffix}"
    optimized_path = OPTIMIZED_MEDIA_DIR / f"{base_name}.jpg"

    with original_path.open("wb") as original_file:
        original_file.write(data)

    optimized_image = image.copy()
    optimized_image.thumbnail((1600, 1600), Image.LANCZOS)
    optimized_image.save(optimized_path, format="JPEG", optimize=True, quality=85)
    width, height = optimized_image.size
    file_size = optimized_path.stat().st_size

    return {
        "original_path": str(original_path.relative_to(BASE_DIR.parent)),
        "optimized_path": str(optimized_path.relative_to(BASE_DIR.parent)),
        "width": width,
        "height": height,
        "file_size": file_size,
    }


def compute_outstanding_balance(payments: Iterable[models.Payment], amount_due: float) -> float:
    total_paid = sum(float(payment.amount) for payment in payments)
    return round(amount_due - total_paid, 2)


def get_available_supplier_integrations() -> dict[str, List[str]]:
    """Return the configured supplier integrations and supported resource types."""

    return AVAILABLE_SUPPLIER_INTEGRATIONS


def fetch_supplier_inventory(
    provider: str, resource: str, query: Optional[str] = None
) -> List[dict[str, str]]:
    """Simulate pulling inventory records from an external provider.

    This helper keeps the API surface extensible while returning structured placeholder
    data that downstream itinerary builders can experiment with.
    """

    provider = provider.lower()
    resource = resource.lower()
    if provider not in AVAILABLE_SUPPLIER_INTEGRATIONS:
        raise ValueError(f"Unknown provider '{provider}'")
    if resource not in AVAILABLE_SUPPLIER_INTEGRATIONS[provider]:
        raise ValueError(f"Resource '{resource}' unsupported for provider '{provider}'")

    sample_data: List[dict[str, str]] = []
    if provider == "amadeus" and resource == "hotels":
        sample_data = [
            {
                "name": "Seaside Retreat",
                "city": query or "Cape Town",
                "rate_code": f"HOT-{randint(1000, 9999)}",
                "currency": "USD",
                "price": "189.00",
            },
            {
                "name": "Mountain Lodge",
                "city": query or "Nairobi",
                "rate_code": f"HOT-{randint(1000, 9999)}",
                "currency": "USD",
                "price": "149.00",
            },
        ]
    elif provider == "amadeus" and resource == "flights":
        sample_data = [
            {
                "carrier": "KQ",
                "flight_number": f"{randint(100, 999)}",
                "origin": (query or "NBO-LHR").split("-")[0],
                "destination": (query or "NBO-LHR").split("-")[1],
                "fare": "720.00",
            }
        ]
    elif resource == "lodges":
        sample_data = [
            {
                "name": "Savannah Plains Camp",
                "location": query or "Masai Mara",
                "board_basis": "Full Board",
                "price": "320.00",
            }
        ]
    else:  # transport or other local resources
        sample_data = [
            {
                "provider": "City Transfers",
                "vehicle": "Luxury Van",
                "route": query or "Airport - Hotel",
                "price": "80.00",
            }
        ]

    return sample_data


def remove_media_files(asset: models.MediaAsset) -> None:
    """Delete stored media asset files when an asset record is removed."""

    for relative_path in (asset.original_path, asset.optimized_path):
        if not relative_path:
            continue
        file_path = BASE_DIR.parent / relative_path
        if file_path.exists():  # pragma: no branch - simple filesystem check
            file_path.unlink()
