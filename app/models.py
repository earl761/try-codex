"""SQLAlchemy models for the Tour Planner backend."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TravelAgency(Base, TimestampMixin):
    __tablename__ = "travel_agencies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True)
    slug = Column(String(160), nullable=False, unique=True)
    contact_email = Column(String(120), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    website = Column(String(200), nullable=True)
    address = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    default_currency = Column(String(10), nullable=False, default="USD")
    logo_url = Column(String(255), nullable=True)
    brand_primary_color = Column(String(20), nullable=True)
    brand_secondary_color = Column(String(20), nullable=True)
    invoice_footer = Column(Text, nullable=True)

    users = relationship("User", back_populates="agency", cascade="all, delete-orphan")
    integrations = relationship(
        "IntegrationCredential", back_populates="agency", cascade="all, delete-orphan"
    )
    clients = relationship("Client", back_populates="agency")
    leads = relationship("Lead", back_populates="agency")
    suppliers = relationship("Supplier", back_populates="agency")
    media_assets = relationship(
        "MediaAsset", back_populates="agency", cascade="all, delete-orphan"
    )


class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), nullable=True, unique=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    agency_id = Column(Integer, ForeignKey("travel_agencies.id"), nullable=True)

    itineraries = relationship("Itinerary", back_populates="client", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="client", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="client", cascade="all, delete-orphan")
    agency = relationship("TravelAgency", back_populates="clients")


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), nullable=True)
    source = Column(String(120), nullable=True)
    status = Column(String(50), nullable=False, default="new")
    notes = Column(Text, nullable=True)
    agency_id = Column(Integer, ForeignKey("travel_agencies.id"), nullable=True)

    client = relationship("Client", back_populates="leads")
    agency = relationship("TravelAgency", back_populates="leads")


class TourPackage(Base, TimestampMixin):
    __tablename__ = "tour_packages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    destination = Column(String(150), nullable=False)
    duration_days = Column(Integer, nullable=False)
    base_price = Column(Numeric(10, 2), nullable=False)
    description = Column(Text, nullable=True)

    itineraries = relationship("Itinerary", back_populates="tour_package")


class Itinerary(Base, TimestampMixin):
    __tablename__ = "itineraries"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    tour_package_id = Column(Integer, ForeignKey("tour_packages.id"), nullable=True)
    title = Column(String(150), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=True)
    status = Column(String(50), nullable=False, default="draft")
    estimate_amount = Column(Numeric(10, 2), nullable=True)
    estimate_currency = Column(String(10), nullable=False, default="USD")
    brand_logo_url = Column(String(255), nullable=True)
    brand_primary_color = Column(String(20), nullable=True)
    brand_secondary_color = Column(String(20), nullable=True)
    brand_footer_note = Column(Text, nullable=True)

    client = relationship("Client", back_populates="itineraries")
    tour_package = relationship("TourPackage", back_populates="itineraries")
    items = relationship("ItineraryItem", back_populates="itinerary", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="itinerary")
    extensions = relationship(
        "ItineraryExtension", back_populates="itinerary", cascade="all, delete-orphan"
    )
    notes = relationship(
        "ItineraryNote", back_populates="itinerary", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="check_dates"),
    )


class ItineraryItem(Base, TimestampMixin):
    __tablename__ = "itinerary_items"

    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id"), nullable=False)
    day_number = Column(Integer, nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(150), nullable=True)
    start_time = Column(String(20), nullable=True)
    end_time = Column(String(20), nullable=True)
    category = Column(String(50), nullable=False, default="activity")
    supplier_reference = Column(String(120), nullable=True)
    estimated_cost = Column(Numeric(10, 2), nullable=True)
    estimated_currency = Column(String(10), nullable=False, default="USD")

    itinerary = relationship("Itinerary", back_populates="items")
    media_links = relationship(
        "ItineraryItemMedia",
        back_populates="itinerary_item",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id"), nullable=True)
    issue_date = Column(Date, default=date.today, nullable=False)
    due_date = Column(Date, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    status = Column(String(50), nullable=False, default="unpaid")

    client = relationship("Client", back_populates="invoices")
    itinerary = relationship("Itinerary", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    paid_on = Column(Date, default=date.today, nullable=False)
    method = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)

    invoice = relationship("Invoice", back_populates="payments")


class Expense(Base, TimestampMixin):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(200), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    category = Column(String(100), nullable=True)
    incurred_on = Column(Date, default=date.today, nullable=False)
    reimbursable = Column(Boolean, default=False)


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    supplier_type = Column(
        String(50), nullable=False, default="lodging", doc="Category such as lodging or transport"
    )
    description = Column(Text, nullable=True)
    contact_email = Column(String(120), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    website = Column(String(200), nullable=True)
    location = Column(String(120), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)
    integration_provider = Column(
        String(100), nullable=True, doc="External provider powering automatic rate sync"
    )
    integration_reference = Column(
        String(100), nullable=True, doc="Reference code used by the integration provider"
    )
    agency_id = Column(Integer, ForeignKey("travel_agencies.id"), nullable=True)

    rates = relationship(
        "SupplierRate", back_populates="supplier", cascade="all, delete-orphan", passive_deletes=True
    )
    agency = relationship("TravelAgency", back_populates="suppliers")


class SupplierRate(Base, TimestampMixin):
    __tablename__ = "supplier_rates"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(150), nullable=False)
    category = Column(
        String(50),
        nullable=False,
        default="accommodation",
        doc="Type of inventory e.g. accommodation, transport, activity, flight",
    )
    description = Column(Text, nullable=True)
    rate_type = Column(
        String(50),
        nullable=False,
        default="per_night",
        doc="Billing cadence such as per_night, per_trip, per_person",
    )
    unit = Column(String(50), nullable=True)
    capacity = Column(Integer, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)
    refundable = Column(Boolean, nullable=False, default=True)
    external_code = Column(
        String(120), nullable=True, doc="Identifier provided by an external system"
    )
    availability_notes = Column(Text, nullable=True)

    supplier = relationship("Supplier", back_populates="rates")

    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_supplier_rates_valid_dates",
        ),
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), nullable=False, unique=True)
    full_name = Column(String(120), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    whatsapp_number = Column(String(50), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    agency_id = Column(Integer, ForeignKey("travel_agencies.id"), nullable=True)
    two_factor_secret = Column(String(32), nullable=True)
    two_factor_enabled = Column(Boolean, nullable=False, default=False)

    agency = relationship("TravelAgency", back_populates="users")
    notifications = relationship("NotificationLog", back_populates="user")
    media_uploads = relationship("MediaAsset", back_populates="uploaded_by")


class IntegrationCredential(Base, TimestampMixin):
    __tablename__ = "integration_credentials"

    __table_args__ = (UniqueConstraint("agency_id", "provider", name="uq_agency_provider"),)

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(100), nullable=False)
    api_key = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    agency_id = Column(Integer, ForeignKey("travel_agencies.id"), nullable=False)

    agency = relationship("TravelAgency", back_populates="integrations")


class NotificationLog(Base, TimestampMixin):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(120), nullable=False)
    channel = Column(String(50), nullable=False)
    recipient = Column(String(150), nullable=False)
    subject = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="queued")
    context = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", back_populates="notifications")


class SiteSetting(Base, TimestampMixin):
    __tablename__ = "site_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(120), nullable=False, unique=True)
    value = Column(Text, nullable=False)


class MediaAsset(Base, TimestampMixin):
    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True, index=True)
    agency_id = Column(Integer, ForeignKey("travel_agencies.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    original_path = Column(String(255), nullable=False)
    optimized_path = Column(String(255), nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)
    alt_text = Column(String(255), nullable=True)
    tags = Column(String(255), nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    agency = relationship("TravelAgency", back_populates="media_assets")
    uploaded_by = relationship("User", back_populates="media_uploads")
    item_links = relationship(
        "ItineraryItemMedia",
        back_populates="asset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ItineraryItemMedia(Base, TimestampMixin):
    __tablename__ = "itinerary_item_media"

    id = Column(Integer, primary_key=True, index=True)
    itinerary_item_id = Column(
        Integer,
        ForeignKey("itinerary_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    media_asset_id = Column(
        Integer,
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    usage = Column(
        String(50),
        nullable=False,
        default="gallery",
        doc="Context for the image such as activity, accommodation, or transport",
    )

    itinerary_item = relationship("ItineraryItem", back_populates="media_links")
    asset = relationship("MediaAsset", back_populates="item_links")


class ItineraryExtension(Base, TimestampMixin):
    __tablename__ = "itinerary_extensions"

    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    additional_cost = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(10), nullable=False, default="USD")

    itinerary = relationship("Itinerary", back_populates="extensions")


class ItineraryNote(Base, TimestampMixin):
    __tablename__ = "itinerary_notes"

    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False)
    category = Column(
        String(50),
        nullable=False,
        default="custom",
        doc="Note category such as packing, visa, terms, or destination",
    )
    title = Column(String(150), nullable=True)
    content = Column(Text, nullable=False)

    itinerary = relationship("Itinerary", back_populates="notes")
