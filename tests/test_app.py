from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import Base  # noqa: E402
from app.main import app, get_db  # noqa: E402

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


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


def test_create_itinerary_and_print(api_client: TestClient) -> None:
    client_id = create_sample_client(api_client)
    itinerary_payload = {
        "client_id": client_id,
        "title": "Bali Adventure",
        "start_date": str(date(2024, 6, 1)),
        "end_date": str(date(2024, 6, 5)),
        "status": "confirmed",
        "items": [
            {
                "day_number": 1,
                "title": "Arrival",
                "description": "Airport pickup and hotel check-in.",
                "location": "Denpasar",
            },
            {
                "day_number": 2,
                "title": "Beach Day",
                "description": "Relax at Nusa Dua Beach.",
                "location": "Nusa Dua",
            },
        ],
    }

    itinerary_response = api_client.post("/itineraries", json=itinerary_payload)
    assert itinerary_response.status_code == 201
    itinerary_id = itinerary_response.json()["id"]

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
    data = summary.json()
    assert data["total_invoiced"] == 1500.0
    assert data["total_paid"] == 500.0
    assert data["total_expenses"] == 300.0
    assert data["outstanding"] == 1000.0
    assert data["profitability"] == 200.0


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
