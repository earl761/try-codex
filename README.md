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
- **Flight Booking Panel**: Search Amadeus inventory, build flight bookings with PNRs, issue tickets with printable confirmations, and control access via dedicated or premium subscription packages.
- **Media Library & Optimization**: Upload images for itineraries, automatically optimize them for web delivery, and manage the gallery from the admin console.
- **Subscription Packages**: Configure travel-agency subscription plans, toggle included modules (core platform, flight booking add-on), and surface pricing on the SEO landing page.
- **Authentication & 2FA**: Email-based signup/login with optional TOTP two-factor activation for additional security.
- **Notifications**: Automatic email and WhatsApp notification logs for client, itinerary, finance, supplier, and integration events.
- **Admin Console**: Manage travel agencies, integration API keys, site settings, and review notification history.
- **SEO Landing Page**: A marketing-focused landing page powered by Jinja2 with customizable meta tags managed through admin settings.
- **Collaborative Itinerary Studio**: Invite teammates as viewers, editors, or approvers, capture threaded comments, and maintain automatic version history with pricing snapshots.
- **AI-Assisted Enhancements**: Request contextual activity, margin, or traveler-support suggestions to strengthen each proposal before sending.
- **Dynamic Pricing Controls**: Configure flat or percentage markups, monitor calculated margins, and generate profitability summaries for every itinerary.
- **Document Automation**: Instantly render travel briefs, visa support letters, and traveler waivers aligned to agency branding.
- **Client Portal**: Share a mobile-first portal for traveler approvals, waiver signatures, and payment method discovery via secure invitations.
- **Analytics Overview**: Surface booking KPIs, revenue trends, and average margins through the admin analytics endpoint.

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
│       ├── flights.py
│       ├── itineraries.py
│       ├── leads.py
│       ├── media.py
│       ├── portal.py
│       ├── reports.py
│       ├── suppliers.py
│       └── tour_packages.py
├── crud.py          # Database helper operations
├── database.py      # SQLAlchemy configuration
├── main.py          # FastAPI application factory
├── models.py        # SQLAlchemy ORM models
├── schemas.py       # Pydantic models for validation
├── templates/       # Jinja2 templates for itineraries, tickets, and landing page
│   ├── client_portal.html
│   ├── flight_ticket.html
│   ├── itinerary.html        # compatibility include for the classic layout
│   ├── itinerary_classic.html
│   ├── itinerary_modern.html
│   ├── itinerary_gallery.html
│   ├── landing.html
│   ├── travel_brief.html
│   ├── traveler_waiver.html
│   └── visa_letter.html
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
- `POST /itineraries/{id}/invoice` – convert an itinerary estimate into a finance invoice in one call.
- `GET /itineraries/{id}/pricing` – review base costs, markup values, and calculated margins for an itinerary.
- `GET /itineraries/{id}/suggestions` – request AI-assisted enhancements across pricing, activities, or traveler support.
- `GET /itineraries/{id}/documents/{type}` – download travel briefs, visa support letters, or waiver templates.
- `POST /itineraries/{id}/collaborators` – grant edit/comment access to teammates.
- `POST /itineraries/{id}/comments` – capture collaboration feedback and mark threads as resolved.
- `POST /finance/invoices` – issue an invoice linked to a client or itinerary.
- `POST /leads/{id}/convert` – create a client record from a qualified lead.
- `POST /itineraries/{id}/duplicate` – clone an itinerary as a reusable template.
- `GET /finance/summary` – view totals for invoices, payments, expenses, and profitability.
- `GET /finance/payment-providers` – inspect supported payment providers and their capabilities.
- `POST /finance/payments/initiate` – kick off a payment against an invoice using MTN MoMo, Airtel Money, Stripe, or PayPal.
- `GET /flights/providers` – review enabled flight distribution partners and capabilities.
- `GET /flights/search` – surface Amadeus fare options for one-way, round-trip, or multi-city journeys (`segments` accepts a JSON array of `{origin, destination, departure_date}` objects when `trip_type=multi_city`).
- `POST /flights/bookings` – create a flight booking with passenger manifests, segments, and automatic notifications.
- `POST /flights/{id}/ticket` – capture ticket numbers/document URLs and notify clients when ticketing is complete.
- `GET /flights/{id}/ticket` – render a branded HTML ticket confirmation ready for printing or PDF export.
- `POST /suppliers` – onboard supplier partners with contact information and integration metadata.
- `POST /suppliers/{id}/rates` – manage supplier rate cards that feed into itinerary pricing.
- `POST /media/assets` – upload an image, store the original, and produce an optimized rendition for itineraries.
- `GET /admin/media` – review, update, or delete media assets across the platform.
- `POST /admin/packages` – create subscription packages for travel agencies and highlight them on the landing page.
- `POST /admin/subscriptions` – enroll a travel agency into a subscription package and trigger notifications.
- `POST /portal/invitations` – invite travelers into the client portal to approve itineraries and sign waivers.
- `GET /portal/invitations/{token}` – fetch portal context (documents, pricing, payment options) or render the traveler page.
- `GET /admin/analytics/overview` – retrieve headline KPIs plus monthly revenue trends for the business.
- `GET /suppliers/integrations/{provider}/{resource}` – preview data structures for external APIs (Amadeus hotels/flights, etc.).
- `POST /admin/agencies` – manage travel agencies from the admin console.
- `POST /admin/api-keys` – store provider API keys (e.g., Amadeus) scoped to an agency.
- `POST /admin/payment-gateways` – configure payment gateway credentials per agency and toggle availability.
- `GET /admin/notifications` – audit recent email/WhatsApp notifications and delivery metadata.
- `PUT /admin/settings/{key}` – override landing page headlines, SEO descriptions, and keywords.

## SaaS Readiness Roadmap

Looking to commercialize the platform? Review the [SaaS Readiness Roadmap](docs/saas_roadmap.md) for a curated backlog covering operational foundations (multi-tenant isolation, billing, audit trails), revenue-driving add-ons (marketplace upsells, dynamic packaging, automation), growth levers (referrals, public APIs, in-app guidance), and enterprise capabilities (SLAs, SSO, data residency).

Refer to the auto-generated docs for the full list of endpoints and payload schemas.

## Notifications & Two-Factor Workflow

1. **Signup/Login** – Create a user via `/auth/signup` and authenticate via `/auth/login`. If the user has enabled 2FA, `two_factor_required` will be `true` and a valid TOTP code must be supplied on a subsequent login request.
2. **Enable 2FA** – Call `/auth/2fa/setup` to obtain the provisioning URI and shared secret. After scanning or entering the secret into an authenticator app, confirm the generated code via `/auth/2fa/activate`.
3. **Notification Logs** – Most client, itinerary, finance, supplier, agency, and integration actions automatically enqueue an email and/or WhatsApp notification log. Administrators can review these entries with `/admin/notifications` or view aggregated counts at `/admin/notifications/summary`.
