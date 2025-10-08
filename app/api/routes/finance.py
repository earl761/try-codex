"""Finance endpoints covering invoices, payments, expenses, and integrations."""
from __future__ import annotations

from datetime import date
"""Finance endpoints covering invoices, payments, and expenses."""
from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ... import crud, models, schemas
from ...utils import (
    compute_outstanding_balance,
    initiate_payment_with_provider,
    list_supported_payment_providers,
)
from ...utils import compute_outstanding_balance
from ..deps import get_db

router = APIRouter(prefix="/finance", tags=["finance"])


@router.post("/invoices", response_model=schemas.Invoice, status_code=status.HTTP_201_CREATED)
def create_invoice(invoice_in: schemas.InvoiceCreate, db: Session = Depends(get_db)) -> models.Invoice:
    invoice = crud.create_invoice(db, invoice_in)
    db.refresh(invoice)
    return invoice


@router.get("/invoices", response_model=List[schemas.Invoice])
def list_invoices(db: Session = Depends(get_db)) -> List[models.Invoice]:
    return list(crud.list_invoices(db))


@router.get("/invoices/{invoice_id}", response_model=schemas.Invoice)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)) -> models.Invoice:
    invoice = crud.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@router.put("/invoices/{invoice_id}", response_model=schemas.Invoice)
def update_invoice(
    invoice_id: int,
    invoice_in: schemas.InvoiceUpdate,
    db: Session = Depends(get_db),
) -> models.Invoice:
    invoice = crud.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    invoice = crud.update_invoice(db, invoice, invoice_in)
    db.refresh(invoice)
    return invoice


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)) -> Response:
    invoice = crud.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    crud.delete_invoice(db, invoice)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/payments", response_model=schemas.Payment, status_code=status.HTTP_201_CREATED)
def create_payment(payment_in: schemas.PaymentCreate, db: Session = Depends(get_db)) -> models.Payment:
    payload = payment_in.model_dump()
    provider = payload.get("provider", "manual")
    if provider != "manual" and not payload.get("transaction_reference"):
        try:
            initiation = initiate_payment_with_provider(
                provider,
                payment_in.amount,
                payment_in.currency,
                customer_reference=payment_in.notes,
            )
        except ValueError as exc:  # pragma: no cover - validation branch
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        payload.update(
            {
                "provider": initiation["provider"],
                "transaction_reference": initiation["transaction_reference"],
                "status": initiation["status"],
                "method": initiation["method"],
                "fee_amount": initiation["fee_amount"],
                "provider_metadata": initiation["metadata"],
            }
        )
        payment_in = schemas.PaymentCreate(**payload)

    payment = crud.create_payment(db, payment_in)
    db.refresh(payment)
    return payment


@router.get("/payments", response_model=List[schemas.Payment])
def list_payments(db: Session = Depends(get_db)) -> List[models.Payment]:
    return list(crud.list_payments(db))


@router.get(
    "/payment-providers",
    response_model=List[schemas.PaymentProviderInfo],
    summary="List supported payment providers",
)
def payment_providers() -> List[schemas.PaymentProviderInfo]:
    providers = list_supported_payment_providers()
    return [schemas.PaymentProviderInfo(**provider) for provider in providers]


@router.post(
    "/payments/initiate",
    response_model=schemas.PaymentInitiationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a payment via a connected provider",
)
def initiate_payment(
    payload: schemas.PaymentInitiationRequest, db: Session = Depends(get_db)
) -> schemas.PaymentInitiationResponse:
    invoice = crud.get_invoice(db, payload.invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    try:
        result = initiate_payment_with_provider(
            payload.provider, payload.amount, payload.currency, payload.customer_reference
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    payment = crud.create_payment(
        db,
        schemas.PaymentCreate(
            invoice_id=payload.invoice_id,
            amount=payload.amount,
            currency=payload.currency,
            paid_on=date.today(),
            method=result["method"],
            provider=result["provider"],
            status=result["status"],
            transaction_reference=result["transaction_reference"],
            fee_amount=result["fee_amount"],
            provider_metadata=result["metadata"],
            notes=payload.customer_reference,
        ),
    )
    db.refresh(payment)

    message = (
        "Payment requires customer action to complete."
        if result["checkout_url"]
        else "Payment processed successfully."
    )

    return schemas.PaymentInitiationResponse(
        provider=result["provider"],
        status=payment.status,
        transaction_reference=payment.transaction_reference or result["transaction_reference"],
        checkout_url=result["checkout_url"],
        message=message,
        payment_id=payment.id,
    )


@router.put("/payments/{payment_id}", response_model=schemas.Payment)
def update_payment(
    payment_id: int,
    payment_in: schemas.PaymentUpdate,
    db: Session = Depends(get_db),
) -> models.Payment:
    payment = crud.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    payment = crud.update_payment(db, payment, payment_in)
    db.refresh(payment)
    return payment


@router.delete("/payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(payment_id: int, db: Session = Depends(get_db)) -> Response:
    payment = crud.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    crud.delete_payment(db, payment)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/expenses", response_model=schemas.Expense, status_code=status.HTTP_201_CREATED)
def create_expense(expense_in: schemas.ExpenseCreate, db: Session = Depends(get_db)) -> models.Expense:
    expense = crud.create_expense(db, expense_in)
    db.refresh(expense)
    return expense


@router.get("/expenses", response_model=List[schemas.Expense])
def list_expenses(db: Session = Depends(get_db)) -> List[models.Expense]:
    return list(crud.list_expenses(db))


@router.put("/expenses/{expense_id}", response_model=schemas.Expense)
def update_expense(
    expense_id: int,
    expense_in: schemas.ExpenseUpdate,
    db: Session = Depends(get_db),
) -> models.Expense:
    expense = crud.get_expense(db, expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    expense = crud.update_expense(db, expense, expense_in)
    db.refresh(expense)
    return expense


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int, db: Session = Depends(get_db)) -> Response:
    expense = crud.get_expense(db, expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    crud.delete_expense(db, expense)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary")
def finance_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    invoices: List[models.Invoice] = list(crud.list_invoices(db))
    payments: List[models.Payment] = list(crud.list_payments(db))
    expenses: List[models.Expense] = list(crud.list_expenses(db))

    total_invoiced = sum(float(invoice.amount) for invoice in invoices)
    total_paid = sum(
        float(payment.amount)
        for payment in payments
        if (payment.status or "completed").lower() == "completed"
    )
    total_paid = sum(float(payment.amount) for payment in payments)
    total_expenses = sum(float(expense.amount) for expense in expenses)

    outstanding = sum(
        compute_outstanding_balance(invoice.payments, float(invoice.amount)) for invoice in invoices
    )
    profitability = round(total_paid - total_expenses, 2)

    return {
        "total_invoiced": round(total_invoiced, 2),
        "total_paid": round(total_paid, 2),
        "total_expenses": round(total_expenses, 2),
        "outstanding": round(outstanding, 2),
        "profitability": profitability,
    }
