"""SQLAlchemy models for the Tour Planner backend."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), nullable=True, unique=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)

    itineraries = relationship("Itinerary", back_populates="client", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="client", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="client", cascade="all, delete-orphan")


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), nullable=True)
    source = Column(String(120), nullable=True)
    status = Column(String(50), nullable=False, default="new")
    notes = Column(Text, nullable=True)

    client = relationship("Client", back_populates="leads")


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

    client = relationship("Client", back_populates="itineraries")
    tour_package = relationship("TourPackage", back_populates="itineraries")
    items = relationship("ItineraryItem", back_populates="itinerary", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="itinerary")

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

    itinerary = relationship("Itinerary", back_populates="items")


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

