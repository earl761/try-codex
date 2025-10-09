from __future__ import annotations

import io
import shutil
import json
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

from app import crud, schemas  # noqa: E402
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
def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


reset_database()


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
        db.commit()
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def create_super_admin_user(email: str = "founder@tourplanner.example") -> str:
    with TestingSessionLocal() as session:
        crud.create_user(
            session,
            schemas.UserCreate(
                email=email,
                password="SuperAdmin#2024",
                full_name="Platform Owner",
                is_admin=True,
                is_super_admin=True,
                role="super_admin",
            ),
        )
        session.commit()
    return email


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


def create_sample_itinerary(client: TestClient, client_id: int) -> int:
    payload = {
        "client_id": client_id,
        "title": "Collaborative Safari",
        "start_date": str(date(2024, 7, 1)),
        "end_date": str(date(2024, 7, 5)),
        "status": "proposal",
        "estimate_amount": "1200.00",
        "estimate_currency": "USD",
        "items": [
            {
                "day_number": 1,
                "title": "Arrival",
                "description": "Airport transfer and welcome dinner.",
                "location": "Arusha",
                "category": "transport",
                "estimated_cost": "150.00",
            }
        ],
        "notes": [
            {
                "category": "custom",
                "content": "Remember to carry copies of your passport and insurance.",
            }
        ],
    }
    response = client.post("/itineraries", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def test_create_itinerary_and_print(api_client: TestClient) -> None:
    client_id = create_sample_client(api_client)
    asset_id = upload_sample_media_asset(api_client)
def test_create_itinerary_and_print(api_client: TestClient) -> None:
    client_id = create_sample_client(api_client)
    asset_id = upload_sample_media_asset(api_client)
def test_create_itinerary_and_print(api_client: TestClient) -> None:
    client_id = create_sample_client(api_client)
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

    classic = api_client.get(f"/itineraries/{itinerary_id}/print?layout=classic")
    assert classic.status_code == 200
    classic_html = classic.text
    assert "Bali Adventure" in classic_html
    assert "Powered by Tour Planner" in classic_html
    assert "Day 1" in classic_html
    assert "Extensions & Enhancements" in classic_html
    assert "Travel Briefing" in classic_html
    assert "Client Estimate" in classic_html
    assert "Thank you for choosing Explorer Collective." in classic_html

    modern = api_client.get(f"/itineraries/{itinerary_id}/print?layout=modern")
    assert modern.status_code == 200
    modern_html = modern.text
    assert "Snapshot" in modern_html
    assert "Know Before You Go" in modern_html

    gallery = api_client.get(f"/itineraries/{itinerary_id}/print?layout=gallery")
    assert gallery.status_code == 200
    gallery_html = gallery.text
    assert "Gallery Layout" in gallery_html
    assert "Traveler Notes" in gallery_html
    printable = api_client.get(f"/itineraries/{itinerary_id}/print")
    assert printable.status_code == 200
    html = printable.text
    assert "Bali Adventure" in html
    assert "Day 1" in html
    assert "Optional Extensions" in html
    assert "Traveler Guidance" in html
    assert "Client Estimate" in html
    assert "Thank you for choosing Explorer Collective." in html

    printable = api_client.get(f"/itineraries/{itinerary_id}/print")
    assert printable.status_code == 200
    body = printable.text
    assert "Bali Adventure" in body
    assert "Day 1" in body
    assert "Nusa Dua" in body


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

    providers_response = api_client.get("/finance/payment-providers")
    assert providers_response.status_code == 200
    providers = providers_response.json()
    provider_ids = {provider["id"] for provider in providers}
    assert {"stripe", "paypal", "mtn_momo", "airtel_money"}.issubset(provider_ids)

    initiation_payload = {
        "invoice_id": invoice_id,
        "amount": "500.00",
        "currency": "USD",
        "provider": "stripe",
        "customer_reference": "STR-INV-500",
    }
    initiation_response = api_client.post("/finance/payments/initiate", json=initiation_payload)
    assert initiation_response.status_code == 201
    initiation_body = initiation_response.json()
    assert initiation_body["status"] in {"requires_action", "pending"}
    assert initiation_body["checkout_url"]

    complete_response = api_client.put(
        f"/finance/payments/{initiation_body['payment_id']}",
        json={"status": "completed"},
    )
    assert complete_response.status_code == 200
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
    data = summary.json()
    assert data["total_invoiced"] == 1500.0
    assert data["total_paid"] == 500.0
    assert data["total_expenses"] == 300.0
    assert data["outstanding"] == 1000.0
    assert data["profitability"] == 200.0


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
    assert user_body["role"] == "agency_owner"

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
    super_admin_email = create_super_admin_user()
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
    agency_body = agency_response.json()
    agency_id = agency_body["id"]
    assert agency_body["powered_by_label"].endswith("Powered by Tour Planner")
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

    landing_update_forbidden = api_client.put(
        "/admin/landing-page",
        json={"headline": "Design bespoke tours in minutes"},
    )
    assert landing_update_forbidden.status_code == 403

    landing_payload = {
        "headline": "Design bespoke tours in minutes",
        "subheadline": "Scale your agency with automation and insight.",
        "call_to_action": "Book a demo",
        "seo_description": "Travel CRM and itinerary software for ambitious agencies.",
        "hero_image_url": "https://cdn.example.com/hero.png",
        "meta_keywords": ["travel software", "itinerary builder", "crm"],
    }
    landing_headers = {"X-Admin-Email": super_admin_email}
    landing_update = api_client.put(
        "/admin/landing-page",
        json=landing_payload,
        headers=landing_headers,
    )
    assert landing_update.status_code == 200
    landing_body = landing_update.json()
    assert landing_body["headline"] == landing_payload["headline"]
    assert landing_body["meta_keywords"] == landing_payload["meta_keywords"]

    landing_get_forbidden = api_client.get("/admin/landing-page")
    assert landing_get_forbidden.status_code == 403
    landing_get = api_client.get("/admin/landing-page", headers=landing_headers)
    assert landing_get.status_code == 200
    assert landing_get.json()["seo_description"] == landing_payload["seo_description"]

    landing_page = api_client.get("/")
    assert landing_page.status_code == 200
    assert landing_payload["headline"] in landing_page.text
    assert landing_payload["call_to_action"] in landing_page.text
    assert "travel software,itinerary builder,crm" in landing_page.text
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


def test_agency_staff_management(api_client: TestClient) -> None:
    create_super_admin_user()
    agency_response = api_client.post(
        "/admin/agencies",
        json={
            "name": "Trailfinders",
            "slug": "trailfinders",
            "contact_email": "hello@trailfinders.example",
        },
    )
    assert agency_response.status_code == 201
    agency_id = agency_response.json()["id"]

    staff_payload = {
        "email": "planner@trailfinders.example",
        "password": "PlannerPass123",
        "full_name": "Plan Pro",
        "role": "planner",
    }
    create_response = api_client.post(f"/agencies/{agency_id}/users", json=staff_payload)
    assert create_response.status_code == 201
    staff_body = create_response.json()
    assert staff_body["role"] == "planner"
    assert staff_body["agency_id"] == agency_id

    roster = api_client.get(f"/agencies/{agency_id}/users")
    assert roster.status_code == 200
    assert len(roster.json()) == 1

    update_response = api_client.put(
        f"/agencies/{agency_id}/users/{staff_body['id']}",
        json={"role": "finance"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["role"] == "finance"

    delete_response = api_client.delete(f"/agencies/{agency_id}/users/{staff_body['id']}")
    assert delete_response.status_code == 204

    empty_roster = api_client.get(f"/agencies/{agency_id}/users")
    assert empty_roster.status_code == 200
    assert empty_roster.json() == []


def test_amadeus_search_supports_multi_city(api_client: TestClient) -> None:
    segments_payload = [
        {
            "origin": "NBO",
            "destination": "ADD",
            "departure_date": str(date(2024, 10, 4)),
        },
        {
            "origin": "ADD",
            "destination": "DXB",
            "departure_date": str(date(2024, 10, 8)),
        },
    ]
    params = [
        ("trip_type", "multi_city"),
        ("passengers", "2"),
        ("travel_class", "economy"),
        ("segments", json.dumps(segments_payload)),
    ]
    offers_response = api_client.get("/flights/search", params=params)
    assert offers_response.status_code == 200
    offers = offers_response.json()
    assert offers
    for offer in offers:
        assert len(offer["segments"]) == 2
        assert offer["segments"][0]["origin"] == "NBO"
        assert offer["segments"][-1]["destination"] == "DXB"


def test_flight_booking_requires_subscription(api_client: TestClient) -> None:
    agency_payload = {
        "name": "Skyward Travel",
        "contact_email": "ops@skyward.example",
    }
    agency_response = api_client.post("/admin/agencies", json=agency_payload)
    assert agency_response.status_code == 201
    agency_id = agency_response.json()["id"]

    client_id = create_sample_client(api_client)

    offers_response = api_client.get(
        "/flights/search",
        params={
            "origin": "NBO",
            "destination": "JNB",
            "departure_date": str(date(2024, 9, 10)),
            "passengers": 1,
        },
    )
    assert offers_response.status_code == 200
    offers = offers_response.json()
    assert offers

    offer = offers[0]
    segments = [
        {
            "segment_number": index,
            "origin": segment["origin"],
            "destination": segment["destination"],
            "departure": segment["departure"],
            "arrival": segment["arrival"],
            "carrier": segment["carrier"],
            "flight_number": segment["flight_number"],
            "cabin": segment.get("cabin"),
            "fare_class": segment.get("fare_class"),
        }
        for index, segment in enumerate(offer["segments"], start=1)
    ]

    booking_payload = {
        "agency_id": agency_id,
        "client_id": client_id,
        "provider": "amadeus",
        "provider_offer_id": offer["id"],
        "total_price": offer["total_price"],
        "currency": offer["currency"],
        "passengers": [
            {
                "first_name": "Unauthorised",
                "last_name": "Traveler",
                "passenger_type": "ADT",
            }
        ],
        "segments": segments,
    }

    booking_response = api_client.post("/flights/bookings", json=booking_payload)
    assert booking_response.status_code == 403
    assert booking_response.json()["detail"] == "Agency subscription does not include flight booking"



def test_flight_booking_panel_flow(api_client: TestClient) -> None:
    providers_response = api_client.get("/flights/providers")
    assert providers_response.status_code == 200
    providers = providers_response.json()
    assert providers[0]["id"] == "amadeus"
    assert "flight_booking" in providers[0]["modules"]

    package_payload = {
        "name": "Flight Desk",
        "price": "89.00",
        "currency": "USD",
        "billing_cycle": "monthly",
        "modules": ["flight_booking"],
    }
    package_response = api_client.post("/admin/packages", json=package_payload)
    assert package_response.status_code == 201
    package_id = package_response.json()["id"]

    agency_payload = {
        "name": "Altitude Journeys",
        "contact_email": "bookings@altitude.example",
        "contact_phone": "+15551234567",
    }
    agency_response = api_client.post("/admin/agencies", json=agency_payload)
    assert agency_response.status_code == 201
    agency_id = agency_response.json()["id"]

    subscription_payload = {
        "agency_id": agency_id,
        "package_id": package_id,
    }
    subscription_response = api_client.post("/admin/subscriptions", json=subscription_payload)
    assert subscription_response.status_code == 201

    client_id = create_sample_client(api_client)

    offers_response = api_client.get(
        "/flights/search",
        params={
            "trip_type": "round_trip",
            "origin": "NBO",
            "destination": "JNB",
            "departure_date": str(date(2024, 9, 20)),
            "return_date": str(date(2024, 9, 27)),
            "passengers": 2,
            "travel_class": "business",
        },
    )
    assert offers_response.status_code == 200
    offers = offers_response.json()
    assert len(offers) >= 1

    selected_offer = offers[0]
    segments = [
        {
            "segment_number": index,
            "origin": segment["origin"],
            "destination": segment["destination"],
            "departure": segment["departure"],
            "arrival": segment["arrival"],
            "carrier": segment["carrier"],
            "flight_number": segment["flight_number"],
            "cabin": segment.get("cabin"),
            "fare_class": segment.get("fare_class"),
        }
        for index, segment in enumerate(selected_offer["segments"], start=1)
    ]

    booking_payload = {
        "agency_id": agency_id,
        "client_id": client_id,
        "provider": "amadeus",
        "provider_offer_id": selected_offer["id"],
        "total_price": selected_offer["total_price"],
        "currency": selected_offer["currency"],
        "passengers": [
            {
                "first_name": "Ava",
                "last_name": "Flyer",
                "passenger_type": "ADT",
                "document_number": "P998877",
            },
            {
                "first_name": "Eli",
                "last_name": "Flyer",
                "passenger_type": "ADT",
            },
        ],
        "segments": segments,
        "notes": "Hold premium cabin seats for client approval.",
    }

    booking_response = api_client.post("/flights/bookings", json=booking_payload)
    assert booking_response.status_code == 201
    booking_body = booking_response.json()
    assert booking_body["provider"] == "amadeus"
    assert len(booking_body["segments"]) == len(segments)
    assert len(booking_body["pnr"]) == 6

    list_response = api_client.get("/flights/bookings", params={"agency_id": agency_id})
    assert list_response.status_code == 200
    assert list_response.json()[0]["pnr"] == booking_body["pnr"]

    ticket_payload = {
        "ticket_numbers": ["176000000001", "176000000002"],
        "document_url": "https://example.com/ticket.pdf",
    }
    ticket_response = api_client.post(
        f"/flights/bookings/{booking_body['id']}/ticket", json=ticket_payload
    )
    assert ticket_response.status_code == 200
    ticket_body = ticket_response.json()
    assert ticket_body["status"] == "ticketed"
    assert ticket_body["ticket_numbers"] == ticket_payload["ticket_numbers"]

    ticket_html = api_client.get(f"/flights/bookings/{booking_body['id']}/ticket")
    assert ticket_html.status_code == 200
    assert booking_body["pnr"] in ticket_html.text
    assert "Ava Flyer" in ticket_html.text

def test_itinerary_collaboration_and_documents(api_client: TestClient) -> None:
    client_id = create_sample_client(api_client)
    itinerary_id = create_sample_itinerary(api_client, client_id)

    with TestingSessionLocal() as session:
        collaborator = crud.create_user(
            session,
            schemas.UserCreate(
                email="collab@example.com",
                password="Collaborate123!",
                full_name="Collaborator Coach",
                role="planner",
            ),
        )
        session.commit()
        collaborator_id = collaborator.id

    collab_response = api_client.post(
        f"/itineraries/{itinerary_id}/collaborators",
        json={"user_id": collaborator_id, "role": "editor", "permissions": ["comment"]},
    )
    assert collab_response.status_code == 201
    assert collab_response.json()["user"]["email"] == "collab@example.com"

    collaborators = api_client.get(f"/itineraries/{itinerary_id}/collaborators")
    assert collaborators.status_code == 200
    assert len(collaborators.json()) == 1

    comment_response = api_client.post(
        f"/itineraries/{itinerary_id}/comments",
        json={"author_id": collaborator_id, "body": "Can we add a sunset cruise?"},
    )
    assert comment_response.status_code == 201
    comment_id = comment_response.json()["id"]

    resolve_response = api_client.post(
        f"/itineraries/{itinerary_id}/comments/{comment_id}/resolve",
        json={"resolved": True},
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["resolved"] is True

    update_response = api_client.put(
        f"/itineraries/{itinerary_id}",
        json={"status": "sent", "target_margin": "20.00", "markup_strategy": "percentage"},
    )
    assert update_response.status_code == 200

    versions = api_client.get(f"/itineraries/{itinerary_id}/versions")
    assert versions.status_code == 200
    assert versions.json()[0]["version_number"] >= 1

    pricing = api_client.get(f"/itineraries/{itinerary_id}/pricing")
    assert pricing.status_code == 200
    pricing_body = pricing.json()
    assert pricing_body["total_price"]

    suggestions = api_client.get(
        f"/itineraries/{itinerary_id}/suggestions", params={"focus": "pricing"}
    )
    assert suggestions.status_code == 200
    assert len(suggestions.json()) >= 1

    brief = api_client.get(f"/itineraries/{itinerary_id}/documents/travel_brief")
    assert brief.status_code == 200
    assert "Travel Brief" in brief.text

    visa_letter = api_client.get(f"/itineraries/{itinerary_id}/documents/visa_letter")
    assert visa_letter.status_code == 200
    assert "Visa Support Letter" in visa_letter.text

    bad_doc = api_client.get(f"/itineraries/{itinerary_id}/documents/unknown")
    assert bad_doc.status_code == 400

    itinerary_detail = api_client.get(f"/itineraries/{itinerary_id}")
    assert itinerary_detail.status_code == 200
    body = itinerary_detail.json()
    assert body["comments"][0]["body"] == "Can we add a sunset cruise?"
    assert body["collaborators"][0]["user"]["email"] == "collab@example.com"


def test_portal_invitation_and_analytics(api_client: TestClient) -> None:
    client_id = create_sample_client(api_client)
    itinerary_id = create_sample_itinerary(api_client, client_id)

    invitation_response = api_client.post(
        "/portal/invitations",
        json={"itinerary_id": itinerary_id, "client_id": client_id, "expires_in_days": 3},
    )
    assert invitation_response.status_code == 201
    invitation_body = invitation_response.json()
    token = invitation_body["token"]

    portal_view = api_client.get(f"/portal/invitations/{token}")
    assert portal_view.status_code == 200
    view_body = portal_view.json()
    assert view_body["itinerary"]["id"] == itinerary_id
    assert "available_documents" in view_body

    portal_page = api_client.get(f"/portal/invitations/{token}/page")
    assert portal_page.status_code == 200
    assert "Client Portal" in portal_page.text

    decision_response = api_client.post(
        f"/portal/invitations/{token}/decision", json={"decision": "approved"}
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["status"] == "approved"

    waiver_response = api_client.post(
        f"/portal/invitations/{token}/waiver", json={"accepted": True}
    )
    assert waiver_response.status_code == 200
    assert waiver_response.json()["waiver_signed"] is True

    analytics = api_client.get("/admin/analytics/overview")
    assert analytics.status_code == 200
    analytics_body = analytics.json()
    assert analytics_body["total_clients"] == 1
    assert analytics_body["total_itineraries"] >= 1

    delete_response = api_client.delete(f"/portal/invitations/{token}")
    assert delete_response.status_code == 204
