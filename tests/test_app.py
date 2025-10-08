from __future__ import annotations

import io
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
import pyotp
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import Base  # noqa: E402
from app.main import app, get_db  # noqa: E402
from app.utils import MEDIA_ROOT  # noqa: E402

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def reset_media_storage() -> None:
    if MEDIA_ROOT.exists():
        shutil.rmtree(MEDIA_ROOT)


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    reset_media_storage()


reset_database()


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
        db.commit()
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    reset_database()
    with TestClient(app) as client:
        yield client


def create_sample_client(client: TestClient) -> int:
    response = client.post(
        "/clients",
        json={"name": "Alice Traveler", "email": "alice@example.com"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def upload_sample_media_asset(client: TestClient) -> int:
    image = Image.new("RGB", (32, 32), color=(255, 140, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    files = {"file": ("sunset.png", buffer, "image/png")}
    data = {"alt_text": "Sunset vista", "tags": "sunset,beach"}
    response = client.post("/media/assets", files=files, data=data)
    buffer.close()
    assert response.status_code == 201
    body = response.json()
    assert body["optimized_path"].endswith(".jpg")
    return body["id"]


def test_create_itinerary_and_print(api_client: TestClient) -> None:
    client_id = create_sample_client(api_client)
    asset_id = upload_sample_media_asset(api_client)
    itinerary_payload = {
        "client_id": client_id,
        "title": "Bali Adventure",
        "start_date": str(date(2024, 6, 1)),
        "end_date": str(date(2024, 6, 5)),
        "status": "confirmed",
        "estimate_amount": "2750.00",
        "estimate_currency": "USD",
        "brand_logo_url": "https://example.com/logo.png",
        "brand_primary_color": "#1F3A93",
        "brand_secondary_color": "#F39C12",
        "brand_footer_note": "Thank you for choosing Explorer Collective.",
        "items": [
            {
                "day_number": 1,
                "title": "Arrival",
                "description": "Airport pickup and hotel check-in.",
                "location": "Denpasar",
                "category": "transport",
                "estimated_cost": "120.00",
                "media": [{"asset_id": asset_id, "usage": "transport"}],
            },
            {
                "day_number": 2,
                "title": "Beach Day",
                "description": "Relax at Nusa Dua Beach.",
                "location": "Nusa Dua",
                "category": "activity",
                "supplier_reference": "SUP-42",
                "estimated_cost": "320.00",
            },
        ],
        "extensions": [
            {
                "title": "Ubud Cultural Extension",
                "description": "Two additional nights exploring Ubud's temples and rice terraces.",
                "additional_cost": "540.00",
                "currency": "USD",
            }
        ],
        "notes": [
            {
                "category": "packing",
                "title": "Packing Checklist",
                "content": "Light layers, sunscreen, comfortable walking shoes.",
            },
            {
                "category": "visa",
                "content": "Visa on arrival available for most nationalities for 30 days.",
            },
        ],
    }

    itinerary_response = api_client.post("/itineraries", json=itinerary_payload)
    assert itinerary_response.status_code == 201
    itinerary_id = itinerary_response.json()["id"]
    body = itinerary_response.json()
    assert body["estimate_amount"] == "2750.00"
    assert body["extensions"][0]["title"] == "Ubud Cultural Extension"
    assert body["items"][0]["media"][0]["asset"]["alt_text"] == "Sunset vista"

    printable = api_client.get(f"/itineraries/{itinerary_id}/print")
    assert printable.status_code == 200
    html = printable.text
    assert "Bali Adventure" in html
    assert "Day 1" in html
    assert "Optional Extensions" in html
    assert "Traveler Guidance" in html
    assert "Client Estimate" in html
    assert "Thank you for choosing Explorer Collective." in html


def test_finance_summary_flow(api_client: TestClient) -> None:
    client_id = create_sample_client(api_client)

    invoice_payload = {
        "client_id": client_id,
        "issue_date": str(date(2024, 6, 1)),
        "due_date": str(date(2024, 6, 15)),
        "amount": "1500.00",
        "currency": "USD",
    }
    invoice_response = api_client.post("/finance/invoices", json=invoice_payload)
    assert invoice_response.status_code == 201
    invoice_id = invoice_response.json()["id"]

    payment_payload = {
        "invoice_id": invoice_id,
        "amount": "500.00",
        "paid_on": str(date(2024, 6, 2)),
        "currency": "USD",
    }
    payment_response = api_client.post("/finance/payments", json=payment_payload)
    assert payment_response.status_code == 201

    expense_payload = {
        "description": "Hotel deposit",
        "amount": "300.00",
        "incurred_on": str(date(2024, 5, 25)),
        "currency": "USD",
    }
    expense_response = api_client.post("/finance/expenses", json=expense_payload)
    assert expense_response.status_code == 201

    summary = api_client.get("/finance/summary")
    assert summary.status_code == 200


def test_subscription_packages_visible_on_landing(api_client: TestClient) -> None:
    package_payload = {
        "name": "Growth",
        "price": "199.00",
        "currency": "USD",
        "billing_cycle": "monthly",
        "description": "Everything a scaling agency needs to deliver beautiful itineraries.",
        "features": [
            "Unlimited itinerary exports",
            "Branded client portal",
            "Priority supplier support",
        ],
    }
    package_response = api_client.post("/admin/packages", json=package_payload)
    assert package_response.status_code == 201
    package_body = package_response.json()
    assert package_body["slug"].startswith("growth")
    assert len(package_body["features"]) == 3

    agency_payload = {
        "name": "Wander Collective",
        "contact_email": "hello@wander.example",
        "contact_phone": "+15555551212",
        "website": "https://wander.example",
    }
    agency_response = api_client.post("/admin/agencies", json=agency_payload)
    assert agency_response.status_code == 201
    agency_id = agency_response.json()["id"]

    subscription_payload = {
        "agency_id": agency_id,
        "package_id": package_body["id"],
        "notes": "Kick-off trial",
    }
    subscription_response = api_client.post("/admin/subscriptions", json=subscription_payload)
    assert subscription_response.status_code == 201
    subscription_body = subscription_response.json()
    assert subscription_body["package"]["name"] == "Growth"
    assert subscription_body["status"] == "active"

    packages_listing = api_client.get("/admin/packages")
    assert packages_listing.status_code == 200
    assert len(packages_listing.json()) == 1

    subscriptions_listing = api_client.get("/admin/subscriptions", params={"agency_id": agency_id})
    assert subscriptions_listing.status_code == 200
    listing_body = subscriptions_listing.json()
    assert listing_body[0]["package"]["slug"] == package_body["slug"]

    landing_page = api_client.get("/")
    assert landing_page.status_code == 200
    landing_html = landing_page.text
    assert "Growth" in landing_html
    assert "Unlimited itinerary exports" in landing_html


def test_generate_invoice_from_itinerary(api_client: TestClient) -> None:
    client_id = create_sample_client(api_client)
    asset_id = upload_sample_media_asset(api_client)
    itinerary_payload = {
        "client_id": client_id,
        "title": "Savannah Escape",
        "start_date": str(date(2024, 8, 10)),
        "end_date": str(date(2024, 8, 15)),
        "estimate_amount": "1800.00",
        "estimate_currency": "USD",
        "items": [
            {
                "day_number": 1,
                "title": "Game Drive",
                "category": "activity",
                "estimated_cost": "450.00",
                "media": [{"asset_id": asset_id, "usage": "highlight"}],
            }
        ],
    }
    itinerary_resp = api_client.post("/itineraries", json=itinerary_payload)
    assert itinerary_resp.status_code == 201
    itinerary_id = itinerary_resp.json()["id"]

    invoice_resp = api_client.post(
        f"/itineraries/{itinerary_id}/invoice",
        json={
            "issue_date": str(date(2024, 7, 1)),
            "due_date": str(date(2024, 7, 15)),
            "notes": "Deposit due within 14 days.",
        },
    )
    assert invoice_resp.status_code == 201
    invoice_body = invoice_resp.json()
    assert invoice_body["itinerary_id"] == itinerary_id
    assert invoice_body["amount"] == "1800.00"
    assert invoice_body["currency"] == "USD"


def test_lead_conversion_creates_client(api_client: TestClient) -> None:
    lead_payload = {"name": "New Lead", "email": "lead@example.com", "notes": "Interested in Bali"}
    lead_response = api_client.post("/leads", json=lead_payload)
    assert lead_response.status_code == 201
    lead_id = lead_response.json()["id"]

    conversion = api_client.post(f"/leads/{lead_id}/convert")
    assert conversion.status_code == 200
    body = conversion.json()
    assert body["lead"]["status"] == "converted"
    client_id = body["client"]["id"]

    client = api_client.get(f"/clients/{client_id}")
    assert client.status_code == 200
    assert client.json()["email"] == "lead@example.com"


def test_duplicate_itinerary_creates_draft_copy(api_client: TestClient) -> None:
    client_id = create_sample_client(api_client)
    itinerary_payload = {
        "client_id": client_id,
        "title": "Original Trip",
        "start_date": str(date(2024, 7, 1)),
        "end_date": str(date(2024, 7, 3)),
        "status": "confirmed",
        "items": [
            {
                "day_number": 1,
                "title": "Arrival",
                "description": "Check-in",
            }
        ],
    }
    itinerary_response = api_client.post("/itineraries", json=itinerary_payload)
    assert itinerary_response.status_code == 201
    itinerary_id = itinerary_response.json()["id"]

    clone_response = api_client.post(f"/itineraries/{itinerary_id}/duplicate")
    assert clone_response.status_code == 201
    clone_data = clone_response.json()

    assert clone_data["id"] != itinerary_id
    assert clone_data["title"].startswith("Original Trip")
    assert clone_data["status"] == "draft"
    assert len(clone_data["items"]) == 1


def test_supplier_portal_crud_and_integration(api_client: TestClient) -> None:
    supplier_payload = {
        "name": "Safari Lodge",
        "supplier_type": "lodging",
        "contact_email": "bookings@safarilodge.com",
        "location": "Serengeti",
    }
    supplier_response = api_client.post("/suppliers", json=supplier_payload)
    assert supplier_response.status_code == 201
    supplier_id = supplier_response.json()["id"]

    rate_payload = {
        "title": "Deluxe Tent",
        "category": "accommodation",
        "rate_type": "per_night",
        "price": "420.00",
        "currency": "USD",
        "capacity": 2,
    }
    rate_response = api_client.post(f"/suppliers/{supplier_id}/rates", json=rate_payload)
    assert rate_response.status_code == 201
    rate_id = rate_response.json()["id"]

    rates = api_client.get(f"/suppliers/{supplier_id}/rates")
    assert rates.status_code == 200
    assert len(rates.json()) == 1

    update_response = api_client.put(
        f"/suppliers/{supplier_id}/rates/{rate_id}", json={"price": "395.00", "capacity": 3}
    )
    assert update_response.status_code == 200
    assert update_response.json()["price"] == "395.00"
    assert update_response.json()["capacity"] == 3

    integrations = api_client.get("/suppliers/integrations/providers")
    assert integrations.status_code == 200
    providers = integrations.json()
    assert any(provider["provider"] == "amadeus" for provider in providers)

    inventory = api_client.get("/suppliers/integrations/amadeus/hotels", params={"query": "NBO"})
    assert inventory.status_code == 200
    hotels = inventory.json()
    assert len(hotels) >= 1
    assert hotels[0]["city"] == "NBO"


def test_media_admin_management(api_client: TestClient) -> None:
    asset_id = upload_sample_media_asset(api_client)

    media_listing = api_client.get("/media/assets")
    assert media_listing.status_code == 200
    assert any(asset["id"] == asset_id for asset in media_listing.json())

    admin_listing = api_client.get("/admin/media")
    assert admin_listing.status_code == 200
    assert any(asset["id"] == asset_id for asset in admin_listing.json())

    update_response = api_client.patch(
        f"/admin/media/{asset_id}", json={"alt_text": "Updated Alt", "tags": ["lodge", "pool"]}
    )
    assert update_response.status_code == 200
    assert sorted(update_response.json()["tags"]) == ["lodge", "pool"]

    delete_response = api_client.delete(f"/admin/media/{asset_id}")
    assert delete_response.status_code == 204

    confirm_missing = api_client.get(f"/media/assets/{asset_id}")
    assert confirm_missing.status_code == 404


def test_authentication_with_two_factor(api_client: TestClient) -> None:
    email = "owner@example.com"
    password = "StrongPass123"
    signup_payload = {
        "email": email,
        "password": password,
        "full_name": "Agency Owner",
        "whatsapp_number": "+15555550123",
        "agency_name": "Explorer Collective",
    }
    signup_response = api_client.post("/auth/signup", json=signup_payload)
    assert signup_response.status_code == 201
    user_body = signup_response.json()
    assert user_body["email"] == email
    assert user_body["agency_id"] is not None

    login_response = api_client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["access_token"]
    assert login_body["two_factor_required"] is False

    setup_response = api_client.post(
        "/auth/2fa/setup", json={"email": email, "password": password}
    )
    assert setup_response.status_code == 200
    secret = setup_response.json()["secret"]
    totp = pyotp.TOTP(secret)

    activation_code = totp.now()
    activate_response = api_client.post(
        "/auth/2fa/activate", json={"email": email, "otp_code": activation_code}
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["two_factor_enabled"] is True

    pending_login = api_client.post("/auth/login", json={"email": email, "password": password})
    assert pending_login.status_code == 200
    pending_body = pending_login.json()
    assert pending_body["two_factor_required"] is True
    assert pending_body["access_token"] == ""

    verified_login = api_client.post(
        "/auth/login",
        json={"email": email, "password": password, "otp_code": totp.now()},
    )
    assert verified_login.status_code == 200
    assert verified_login.json()["two_factor_required"] is False
    assert verified_login.json()["access_token"]


def test_admin_controls_and_landing_page(api_client: TestClient) -> None:
    agency_response = api_client.post(
        "/admin/agencies",
        json={
            "name": "Global Journeys",
            "slug": "global-journeys",
            "contact_email": "hello@globaljourneys.com",
            "contact_phone": "+44123456789",
        },
    )
    assert agency_response.status_code == 201
    agency_id = agency_response.json()["id"]

    update_response = api_client.put(
        f"/admin/agencies/{agency_id}",
        json={"description": "Worldwide travel network"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Worldwide travel network"

    credential_response = api_client.post(
        "/admin/api-keys",
        json={
            "provider": "amadeus",
            "api_key": "test-amadeus-key",
            "agency_id": agency_id,
        },
    )
    assert credential_response.status_code == 201
    credential_id = credential_response.json()["id"]

    updated_credential = api_client.put(
        f"/admin/api-keys/{credential_id}",
        json={"description": "Sandbox key", "active": True},
    )
    assert updated_credential.status_code == 200
    assert updated_credential.json()["description"] == "Sandbox key"

    settings_response = api_client.put(
        "/admin/settings/headline",
        json={"value": "Design bespoke tours in minutes"},
    )
    assert settings_response.status_code == 200
    keywords_response = api_client.put(
        "/admin/settings/meta_keywords",
        json={"value": "travel software,itinerary builder,crm"},
    )
    assert keywords_response.status_code == 200

    landing_page = api_client.get("/")
    assert landing_page.status_code == 200
    assert "Design bespoke tours in minutes" in landing_page.text
    assert "meta name=\"keywords\"" in landing_page.text

    notifications = api_client.get("/admin/notifications")
    assert notifications.status_code == 200
    notification_items = notifications.json()
    assert len(notification_items) >= 1

    summary = api_client.get("/admin/notifications/summary")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["total_sent"] >= len(notification_items)

    api_keys = api_client.get("/admin/api-keys")
    assert api_keys.status_code == 200
    assert any(item["provider"] == "amadeus" for item in api_keys.json())

    settings_list = api_client.get("/admin/settings")
    assert settings_list.status_code == 200
    assert any(setting["key"] == "headline" for setting in settings_list.json())
