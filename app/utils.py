"""Utility helpers for itinerary formatting and media management."""
from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from pathlib import Path
from random import randint
from typing import Dict, Iterable, List, Optional
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

SUPPORTED_PAYMENT_PROVIDERS: Dict[str, Dict[str, object]] = {
    "mtn_momo": {
        "display_name": "MTN MoMo",
        "payment_type": "mobile_money",
        "supported_currencies": ["UGX", "GHS", "RWF", "XAF", "XOF", "ZMW"],
        "transaction_fee_percent": 1.5,
        "settlement_timeframe": "Instant to same-day",
        "requires_checkout_url": False,
    },
    "airtel_money": {
        "display_name": "Airtel Money",
        "payment_type": "mobile_money",
        "supported_currencies": ["UGX", "KES", "TZS", "XAF", "XOF"],
        "transaction_fee_percent": 1.8,
        "settlement_timeframe": "Instant",
        "requires_checkout_url": False,
    },
    "stripe": {
        "display_name": "Stripe",
        "payment_type": "card",
        "supported_currencies": ["USD", "EUR", "GBP", "KES", "ZAR"],
        "transaction_fee_percent": 2.9,
        "settlement_timeframe": "2-7 days",
        "requires_checkout_url": True,
    },
    "paypal": {
        "display_name": "PayPal",
        "payment_type": "digital_wallet",
        "supported_currencies": ["USD", "EUR", "GBP", "AUD", "CAD"],
        "transaction_fee_percent": 3.1,
        "settlement_timeframe": "Same-day to 2 days",
        "requires_checkout_url": True,
    },
}

ITINERARY_LAYOUT_TEMPLATES: Dict[str, str] = {
    "classic": "itinerary_classic.html",
    "modern": "itinerary_modern.html",
    "gallery": "itinerary_gallery.html",
}

_ENV = Environment(
    loader=PackageLoader("app", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
    enable_async=False,
)


def _ensure_media_directories() -> None:
    for directory in (ORIGINAL_MEDIA_DIR, OPTIMIZED_MEDIA_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def render_itinerary(itinerary: models.Itinerary, layout: str = "classic") -> str:
    """Render an itinerary into a printable HTML document with the desired layout."""

    normalized_layout = layout.lower()
    template_name = ITINERARY_LAYOUT_TEMPLATES.get(
        normalized_layout, ITINERARY_LAYOUT_TEMPLATES["classic"]
    )
    template = _ENV.get_template(template_name)
    return template.render(itinerary=itinerary, selected_layout=normalized_layout)


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
    total_paid = sum(
        float(payment.amount)
        for payment in payments
        if getattr(payment, "status", "completed") == "completed"
    )
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


def list_supported_payment_providers() -> List[Dict[str, object]]:
    """Return structured metadata about supported payment providers."""

    providers: List[Dict[str, object]] = []
    for identifier, meta in SUPPORTED_PAYMENT_PROVIDERS.items():
        providers.append({"id": identifier, **meta})
    return providers


def initiate_payment_with_provider(
    provider: str,
    amount: Decimal,
    currency: str,
    customer_reference: Optional[str] = None,
) -> Dict[str, object]:
    """Simulate initiating a payment with the configured provider."""

    provider_key = provider.lower()
    if provider_key not in SUPPORTED_PAYMENT_PROVIDERS:
        raise ValueError(f"Provider '{provider}' is not supported")

    metadata = SUPPORTED_PAYMENT_PROVIDERS[provider_key]
    supported_currencies = metadata["supported_currencies"]
    if currency.upper() not in supported_currencies:
        raise ValueError(
            f"Currency '{currency}' is not supported by {metadata['display_name']}"
        )

    reference = f"{provider_key.upper()}-{uuid4().hex[:10].upper()}"
    checkout_url = None
    status = "pending" if metadata["payment_type"] == "mobile_money" else "completed"
    method = metadata["payment_type"]
    if metadata["requires_checkout_url"]:
        checkout_url = f"https://checkout.example/{provider_key}/{reference.lower()}"
        status = "requires_action"

    fee_amount = (
        (amount * Decimal(str(metadata["transaction_fee_percent"]))) / Decimal("100")
    ).quantize(Decimal("0.01"))

    return {
        "provider": provider_key,
        "transaction_reference": reference,
        "status": status,
        "method": method,
        "checkout_url": checkout_url,
        "fee_amount": fee_amount,
        "metadata": {
            "customer_reference": customer_reference,
            "settlement_timeframe": metadata["settlement_timeframe"],
        },
    }


def remove_media_files(asset: models.MediaAsset) -> None:
    """Delete stored media asset files when an asset record is removed."""

    for relative_path in (asset.original_path, asset.optimized_path):
        if not relative_path:
            continue
        file_path = BASE_DIR.parent / relative_path
        if file_path.exists():  # pragma: no branch - simple filesystem check
            file_path.unlink()
