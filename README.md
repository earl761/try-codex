# Tour Planner API

A FastAPI-based backend for travel and tour agencies to manage clients, build printable itineraries, run notifications, and track finances with secure access controls.

## Features

- **Itinerary Builder**: Create multi-day itineraries with detailed day plans, branded estimates, day-level imagery, and generate printable HTML output.
- **Designer Layouts**: Offer three PDF-friendly itinerary layouts (classic timeline, modern dark mode, and photo gallery) with agency branding automatically applied.
- **CRM Tools**: Manage clients and leads, capture notes and statuses, and convert warm leads into clients in one click.
- **Supplier Marketplace**: Capture partner lodges, hotels, transport providers, and their rate cards for itinerary planning.
- **Inventory Management**: Store reusable tour packages and supplier-specific pricing.
- **Finance Module**: Issue invoices, record payments and expenses, initiate gateway transactions, and view profitability summaries and sales reports with monthly rollups.
- **Payment Integrations**: Built-in connectors for MTN MoMo, Airtel Money, Stripe, and PayPal with admin-manageable gateway credentials.
- **Media Library & Optimization**: Upload images for itineraries, automatically optimize them for web delivery, and manage the gallery from the admin console.
- **Subscription Packages**: Configure travel-agency subscription plans that surface on the SEO landing page and drive signups.
- **CRM Tools**: Manage clients and leads, capture notes and statuses, and convert warm leads into clients in one click.
- **Supplier Marketplace**: Capture partner lodges, hotels, transport providers, and their rate cards for itinerary planning.
- **Inventory Management**: Store reusable tour packages and supplier-specific pricing.
- **Finance Module**: Issue invoices, record payments and expenses, and view profitability summaries and sales reports with monthly rollups.
- **Media Library & Optimization**: Upload images for itineraries, automatically optimize them for web delivery, and manage the gallery from the admin console.
- **Authentication & 2FA**: Email-based signup/login with optional TOTP two-factor activation for additional security.
- **Notifications**: Automatic email and WhatsApp notification logs for client, itinerary, finance, supplier, and integration events.
- **Admin Console**: Manage travel agencies, integration API keys, site settings, and review notification history.
- **SEO Landing Page**: A marketing-focused landing page powered by Jinja2 with customizable meta tags managed through admin settings.
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
│       ├── admin.py
│       ├── auth.py
│       ├── clients.py
│       ├── finance.py
│       ├── itineraries.py
│       ├── leads.py
│       ├── media.py
│       ├── reports.py
│       ├── suppliers.py
│       ├── reports.py
│       └── tour_packages.py
├── crud.py          # Database helper operations
├── database.py      # SQLAlchemy configuration
├── main.py          # FastAPI application factory
├── models.py        # SQLAlchemy ORM models
├── schemas.py       # Pydantic models for validation
├── templates/       # Jinja2 templates for printable itineraries and landing page
-│   ├── itinerary.html        # compatibility include for the classic layout
-│   ├── itinerary_classic.html
-│   ├── itinerary_modern.html
-│   └── itinerary_gallery.html
│   └── landing.html
│   ├── itinerary.html
│   └── landing.html
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

- `POST /auth/signup` – register a new travel agency user (optionally creating the agency record).
- `POST /auth/login` – obtain a session token; responds with `two_factor_required` when 2FA must be verified.
- `POST /auth/2fa/setup` & `/auth/2fa/activate` – generate and enable TOTP-based two-factor authentication for a user.
- `POST /clients` – create a client record with automatic notification logging.
- `POST /itineraries` – create a branded itinerary with images, estimate amounts, and email/WhatsApp notifications.
- `GET /itineraries/{id}/print` – render a printable itinerary document (layouts: `classic`, `modern`, `gallery`).
- `GET /itineraries/{id}/print` – render a printable itinerary document.
- `POST /itineraries/{id}/invoice` – convert an itinerary estimate into a finance invoice in one call.
- `POST /finance/invoices` – issue an invoice linked to a client or itinerary.
- `POST /leads/{id}/convert` – create a client record from a qualified lead.
- `POST /itineraries/{id}/duplicate` – clone an itinerary as a reusable template.
- `GET /finance/summary` – view totals for invoices, payments, expenses, and profitability.
- `GET /finance/payment-providers` – inspect supported payment providers and their capabilities.
- `POST /finance/payments/initiate` – kick off a payment against an invoice using MTN MoMo, Airtel Money, Stripe, or PayPal.
- `POST /suppliers` – onboard supplier partners with contact information and integration metadata.
- `POST /suppliers/{id}/rates` – manage supplier rate cards that feed into itinerary pricing.
- `POST /media/assets` – upload an image, store the original, and produce an optimized rendition for itineraries.
- `GET /admin/media` – review, update, or delete media assets across the platform.
- `POST /admin/packages` – create subscription packages for travel agencies and highlight them on the landing page.
- `POST /admin/subscriptions` – enroll a travel agency into a subscription package and trigger notifications.
- `GET /suppliers/integrations/{provider}/{resource}` – preview data structures for external APIs (Amadeus hotels/flights, etc.).
- `POST /admin/agencies` – manage travel agencies from the admin console.
- `POST /admin/api-keys` – store provider API keys (e.g., Amadeus) scoped to an agency.
- `POST /admin/payment-gateways` – configure payment gateway credentials per agency and toggle availability.
- `GET /suppliers/integrations/{provider}/{resource}` – preview data structures for external APIs (Amadeus hotels/flights, etc.).
- `POST /admin/agencies` – manage travel agencies from the admin console.
- `POST /admin/api-keys` – store provider API keys (e.g., Amadeus) scoped to an agency.
- `GET /admin/notifications` – audit recent email/WhatsApp notifications and delivery metadata.
- `PUT /admin/settings/{key}` – override landing page headlines, SEO descriptions, and keywords.

Refer to the auto-generated docs for the full list of endpoints and payload schemas.

## Notifications & Two-Factor Workflow

1. **Signup/Login** – Create a user via `/auth/signup` and authenticate via `/auth/login`. If the user has enabled 2FA, `two_factor_required` will be `true` and a valid TOTP code must be supplied on a subsequent login request.
2. **Enable 2FA** – Call `/auth/2fa/setup` to obtain the provisioning URI and shared secret. After scanning or entering the secret into an authenticator app, confirm the generated code via `/auth/2fa/activate`.
3. **Notification Logs** – Most client, itinerary, finance, supplier, agency, and integration actions automatically enqueue an email and/or WhatsApp notification log. Administrators can review these entries with `/admin/notifications` or view aggregated counts at `/admin/notifications/summary`.
- `POST /clients` – create a client record
- `POST /itineraries` – create an itinerary with day-by-day details
- `GET /itineraries/{id}/print` – render a printable itinerary document
- `POST /finance/invoices` – issue an invoice linked to a client or itinerary
- `POST /leads/{id}/convert` – create a client record from a qualified lead
- `POST /itineraries/{id}/duplicate` – clone an itinerary as a reusable template
- `GET /finance/summary` – view totals for invoices, payments, expenses, and profitability

Refer to the auto-generated docs for the full list of endpoints and payload schemas.
