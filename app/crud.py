"""CRUD helper functions used by the API routers."""
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import models, schemas


# Client helpers

def create_client(session: Session, client_in: schemas.ClientCreate) -> models.Client:
    client = models.Client(**client_in.model_dump())
    session.add(client)
    session.flush()
    return client


def list_clients(session: Session) -> Sequence[models.Client]:
    statement = select(models.Client).order_by(models.Client.name)
    return session.scalars(statement).all()


def get_client(session: Session, client_id: int) -> models.Client | None:
    return session.get(models.Client, client_id)


def update_client(session: Session, client: models.Client, client_in: schemas.ClientUpdate) -> models.Client:
    for field, value in client_in.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    session.add(client)
    session.flush()
    return client


def delete_client(session: Session, client: models.Client) -> None:
    session.delete(client)
    session.flush()


# Lead helpers

def create_lead(session: Session, lead_in: schemas.LeadCreate) -> models.Lead:
    lead = models.Lead(**lead_in.model_dump())
    session.add(lead)
    session.flush()
    return lead


def list_leads(session: Session) -> Sequence[models.Lead]:
    statement = select(models.Lead).order_by(models.Lead.created_at.desc())
    return session.scalars(statement).all()


def get_lead(session: Session, lead_id: int) -> models.Lead | None:
    return session.get(models.Lead, lead_id)


def update_lead(session: Session, lead: models.Lead, lead_in: schemas.LeadUpdate) -> models.Lead:
    for field, value in lead_in.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    session.add(lead)
    session.flush()
    return lead


def delete_lead(session: Session, lead: models.Lead) -> None:
    session.delete(lead)
    session.flush()


def convert_lead_to_client(session: Session, lead: models.Lead) -> models.Client:
    if lead.client:
        return lead.client

    client_data = {
        "name": lead.name,
        "email": lead.email,
        "notes": lead.notes,
    }
    client = models.Client(**{key: value for key, value in client_data.items() if value is not None})
    session.add(client)
    session.flush()

    lead.client_id = client.id
    lead.status = "converted"
    session.add(lead)
    session.flush()
    return client


# Tour package helpers

def create_tour_package(session: Session, package_in: schemas.TourPackageCreate) -> models.TourPackage:
    package = models.TourPackage(**package_in.model_dump())
    session.add(package)
    session.flush()
    return package


def list_tour_packages(session: Session) -> Sequence[models.TourPackage]:
    statement = select(models.TourPackage).order_by(models.TourPackage.name)
    return session.scalars(statement).all()


def get_tour_package(session: Session, package_id: int) -> models.TourPackage | None:
    return session.get(models.TourPackage, package_id)


def update_tour_package(
    session: Session, package: models.TourPackage, package_in: schemas.TourPackageUpdate
) -> models.TourPackage:
    for field, value in package_in.model_dump(exclude_unset=True).items():
        setattr(package, field, value)
    session.add(package)
    session.flush()
    return package


def delete_tour_package(session: Session, package: models.TourPackage) -> None:
    session.delete(package)
    session.flush()


# Itinerary helpers

def create_itinerary(session: Session, itinerary_in: schemas.ItineraryCreate) -> models.Itinerary:
    items_data = itinerary_in.model_dump().pop("items", [])
    itinerary = models.Itinerary(**itinerary_in.model_dump(exclude={"items"}))
    session.add(itinerary)
    session.flush()

    for item in items_data:
        itinerary_item = models.ItineraryItem(itinerary_id=itinerary.id, **item)
        session.add(itinerary_item)
    session.flush()
    return itinerary


def list_itineraries(session: Session) -> Sequence[models.Itinerary]:
    statement = (
        select(models.Itinerary)
        .options(
            selectinload(models.Itinerary.items),
            selectinload(models.Itinerary.client),
            selectinload(models.Itinerary.tour_package),
        )
        .order_by(models.Itinerary.start_date)
    )
    return session.scalars(statement).unique().all()


def get_itinerary(session: Session, itinerary_id: int) -> models.Itinerary | None:
    statement = (
        select(models.Itinerary)
        .where(models.Itinerary.id == itinerary_id)
        .options(
            selectinload(models.Itinerary.items),
            selectinload(models.Itinerary.client),
            selectinload(models.Itinerary.tour_package),
        )
    )
    return session.scalars(statement).unique().first()


def update_itinerary(
    session: Session, itinerary: models.Itinerary, itinerary_in: schemas.ItineraryUpdate
) -> models.Itinerary:
    data = itinerary_in.model_dump(exclude_unset=True)
    items_data = data.pop("items", None)

    for field, value in data.items():
        setattr(itinerary, field, value)

    if items_data is not None:
        itinerary.items.clear()
        session.flush()
        for item in items_data:
            itinerary.items.append(models.ItineraryItem(**item))

    session.add(itinerary)
    session.flush()
    return itinerary


def delete_itinerary(session: Session, itinerary: models.Itinerary) -> None:
    session.delete(itinerary)
    session.flush()


def duplicate_itinerary(session: Session, itinerary: models.Itinerary) -> models.Itinerary:
    clone = models.Itinerary(
        client_id=itinerary.client_id,
        tour_package_id=itinerary.tour_package_id,
        title=f"{itinerary.title} (Copy)",
        start_date=itinerary.start_date,
        end_date=itinerary.end_date,
        total_price=itinerary.total_price,
        status="draft",
    )
    session.add(clone)
    session.flush()

    for item in itinerary.items:
        session.add(
            models.ItineraryItem(
                itinerary_id=clone.id,
                day_number=item.day_number,
                title=item.title,
                description=item.description,
                location=item.location,
                start_time=item.start_time,
                end_time=item.end_time,
            )
        )
    session.flush()
    return clone


# Finance helpers

def create_invoice(session: Session, invoice_in: schemas.InvoiceCreate) -> models.Invoice:
    invoice = models.Invoice(**invoice_in.model_dump())
    session.add(invoice)
    session.flush()
    return invoice


def list_invoices(session: Session) -> Sequence[models.Invoice]:
    statement = (
        select(models.Invoice)
        .options(selectinload(models.Invoice.payments))
        .order_by(models.Invoice.issue_date.desc())
    )
    return session.scalars(statement).unique().all()


def get_invoice(session: Session, invoice_id: int) -> models.Invoice | None:
    statement = (
        select(models.Invoice)
        .where(models.Invoice.id == invoice_id)
        .options(selectinload(models.Invoice.payments))
    )
    return session.scalars(statement).unique().first()


def update_invoice(session: Session, invoice: models.Invoice, invoice_in: schemas.InvoiceUpdate) -> models.Invoice:
    for field, value in invoice_in.model_dump(exclude_unset=True).items():
        setattr(invoice, field, value)
    session.add(invoice)
    session.flush()
    return invoice


def delete_invoice(session: Session, invoice: models.Invoice) -> None:
    session.delete(invoice)
    session.flush()


def create_payment(session: Session, payment_in: schemas.PaymentCreate) -> models.Payment:
    payment = models.Payment(**payment_in.model_dump())
    session.add(payment)
    session.flush()
    return payment


def list_payments(session: Session) -> Sequence[models.Payment]:
    statement = select(models.Payment).order_by(models.Payment.paid_on.desc())
    return session.scalars(statement).all()


def get_payment(session: Session, payment_id: int) -> models.Payment | None:
    return session.get(models.Payment, payment_id)


def update_payment(session: Session, payment: models.Payment, payment_in: schemas.PaymentUpdate) -> models.Payment:
    for field, value in payment_in.model_dump(exclude_unset=True).items():
        setattr(payment, field, value)
    session.add(payment)
    session.flush()
    return payment


def delete_payment(session: Session, payment: models.Payment) -> None:
    session.delete(payment)
    session.flush()


def create_expense(session: Session, expense_in: schemas.ExpenseCreate) -> models.Expense:
    expense = models.Expense(**expense_in.model_dump())
    session.add(expense)
    session.flush()
    return expense


def list_expenses(session: Session) -> Sequence[models.Expense]:
    statement = select(models.Expense).order_by(models.Expense.incurred_on.desc())
    return session.scalars(statement).all()


def get_expense(session: Session, expense_id: int) -> models.Expense | None:
    return session.get(models.Expense, expense_id)


def update_expense(session: Session, expense: models.Expense, expense_in: schemas.ExpenseUpdate) -> models.Expense:
    for field, value in expense_in.model_dump(exclude_unset=True).items():
        setattr(expense, field, value)
    session.add(expense)
    session.flush()
    return expense


def delete_expense(session: Session, expense: models.Expense) -> None:
    session.delete(expense)
    session.flush()


def sales_report(session: Session) -> dict[str, dict[str, float]]:
    invoices = list_invoices(session)
    payments = list_payments(session)

    monthly: dict[str, dict[str, Decimal]] = {}
    for invoice in invoices:
        month = invoice.issue_date.strftime("%Y-%m") if invoice.issue_date else "unknown"
        summary = monthly.setdefault(month, {"invoiced": Decimal("0"), "paid": Decimal("0")})
        summary["invoiced"] += Decimal(invoice.amount)
    for payment in payments:
        month = payment.paid_on.strftime("%Y-%m") if payment.paid_on else "unknown"
        summary = monthly.setdefault(month, {"invoiced": Decimal("0"), "paid": Decimal("0")})
        summary["paid"] += Decimal(payment.amount)

    return {
        "monthly": {
            month: {"invoiced": float(values["invoiced"]), "paid": float(values["paid"])}
            for month, values in sorted(monthly.items())
        }
    }
