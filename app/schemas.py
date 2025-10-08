"""Pydantic schemas describing the API payloads."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientBase(BaseModel):
    name: str = Field(..., description="Client full name")
    email: Optional[str] = Field(None, description="Primary email address")
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None



class Client(ClientBase, TimestampMixin):
    id: int


class LeadBase(BaseModel):
    name: str
    email: Optional[str] = None
    source: Optional[str] = None
    status: str = Field("new", description="Lead status e.g. new, contacted, qualified")
    notes: Optional[str] = None
    client_id: Optional[int] = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    client_id: Optional[int] = None


class LeadConversionResult(BaseModel):
    lead: Lead
    client: Client

    model_config = ConfigDict(from_attributes=True)


class Lead(LeadBase, TimestampMixin):
    id: int


class TourPackageBase(BaseModel):
    name: str
    destination: str
    duration_days: int
    base_price: Decimal
    description: Optional[str] = None


class TourPackageCreate(TourPackageBase):
    pass


class TourPackageUpdate(BaseModel):
    name: Optional[str] = None
    destination: Optional[str] = None
    duration_days: Optional[int] = None
    base_price: Optional[Decimal] = None
    description: Optional[str] = None


class TourPackage(TourPackageBase, TimestampMixin):
    id: int


class ItineraryItemBase(BaseModel):
    day_number: int
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    @field_validator("day_number")
    @classmethod
    def validate_day_number(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("day_number must be greater than zero")
        return value


class ItineraryItemCreate(ItineraryItemBase):
    pass


class ItineraryItem(ItineraryItemBase, TimestampMixin):
    id: int


class ItineraryBase(BaseModel):
    client_id: int
    tour_package_id: Optional[int] = None
    title: str
    start_date: date
    end_date: date
    total_price: Optional[Decimal] = None
    status: str = "draft"


class ItineraryCreate(ItineraryBase):
    items: List[ItineraryItemCreate] = Field(default_factory=list)


class ItineraryUpdate(BaseModel):
    client_id: Optional[int] = None
    tour_package_id: Optional[int] = None
    title: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_price: Optional[Decimal] = None
    status: Optional[str] = None
    items: Optional[List[ItineraryItemCreate]] = None


class Itinerary(ItineraryBase, TimestampMixin):
    id: int
    items: List[ItineraryItem]


class InvoiceBase(BaseModel):
    client_id: int
    itinerary_id: Optional[int] = None
    issue_date: date
    due_date: date
    amount: Decimal
    currency: str = "USD"
    status: str = "unpaid"


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    client_id: Optional[int] = None
    itinerary_id: Optional[int] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    status: Optional[str] = None


class Invoice(InvoiceBase, TimestampMixin):
    id: int


class PaymentBase(BaseModel):
    invoice_id: int
    amount: Decimal
    currency: str = "USD"
    paid_on: date
    method: Optional[str] = None
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    invoice_id: Optional[int] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    paid_on: Optional[date] = None
    method: Optional[str] = None
    notes: Optional[str] = None


class Payment(PaymentBase, TimestampMixin):
    id: int


class ExpenseBase(BaseModel):
    description: str
    amount: Decimal
    currency: str = "USD"
    category: Optional[str] = None
    incurred_on: date
    reimbursable: bool = False


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    incurred_on: Optional[date] = None
    reimbursable: Optional[bool] = None


class Expense(ExpenseBase, TimestampMixin):
    id: int
