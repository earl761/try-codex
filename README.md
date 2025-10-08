# Tour Planner API

A FastAPI-based backend for travel and tour agencies to manage clients, build printable itineraries, and track finances.

## Features

- **Itinerary Builder**: Create multi-day itineraries with detailed day plans and generate printable HTML output.
- **CRM Tools**: Manage clients and leads, capture notes and statuses, and convert warm leads into clients in one click.
- **Inventory Management**: Store reusable tour packages.
- **Finance Module**: Issue invoices, record payments and expenses, and view profitability summaries and sales reports with monthly rollups.
- **Reporting**: Quick summaries for itinerary statuses and monthly sales performance.

## Getting Started

### Requirements

- Python 3.11+
- `pip` for dependency installation

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running the API

```bash
uvicorn app.main:app --reload
```

The API will be available at <http://127.0.0.1:8000>. Interactive documentation is provided at `/docs` (Swagger UI) and `/redoc`.

### Database

SQLite is used by default (stored in `tour_planner.db`). The schema is created automatically on startup. Adjust the connection string in `app/database.py` to target a different database engine.

### Project Structure

```
app/
├── api/
│   ├── __init__.py          # Aggregated API router
│   ├── deps.py              # Shared FastAPI dependencies
│   └── routes/              # Modular endpoint definitions
│       ├── clients.py
│       ├── finance.py
│       ├── itineraries.py
│       ├── leads.py
│       ├── reports.py
│       └── tour_packages.py
├── crud.py          # Database helper operations
├── database.py      # SQLAlchemy configuration
├── main.py          # FastAPI application factory
├── models.py        # SQLAlchemy ORM models
├── schemas.py       # Pydantic models for validation
├── templates/       # Jinja2 templates for printable itineraries
│   └── itinerary.html
├── utils.py         # Helper utilities
requirements.txt
README.md
```

### Testing

Tests rely on FastAPI's `TestClient` and an in-memory SQLite database.

```bash
pytest
```

## API Highlights

- `POST /clients` – create a client record
- `POST /itineraries` – create an itinerary with day-by-day details
- `GET /itineraries/{id}/print` – render a printable itinerary document
- `POST /finance/invoices` – issue an invoice linked to a client or itinerary
- `POST /leads/{id}/convert` – create a client record from a qualified lead
- `POST /itineraries/{id}/duplicate` – clone an itinerary as a reusable template
- `GET /finance/summary` – view totals for invoices, payments, expenses, and profitability

Refer to the auto-generated docs for the full list of endpoints and payload schemas.
