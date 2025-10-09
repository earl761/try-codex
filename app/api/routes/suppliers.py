"""Supplier portal endpoints for managing partner inventory."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from ... import crud, models, schemas
from ...utils import fetch_supplier_inventory, get_available_supplier_integrations
from ..deps import get_db

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.post("", response_model=schemas.Supplier, status_code=status.HTTP_201_CREATED)
def create_supplier(supplier_in: schemas.SupplierCreate, db: Session = Depends(get_db)) -> models.Supplier:
    supplier = crud.create_supplier(db, supplier_in)
    db.refresh(supplier)
    return supplier


@router.get("", response_model=List[schemas.Supplier])
def list_suppliers(db: Session = Depends(get_db)) -> List[models.Supplier]:
    return list(crud.list_suppliers(db))


@router.get("/{supplier_id}", response_model=schemas.Supplier)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)) -> models.Supplier:
    supplier = crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return supplier


@router.put("/{supplier_id}", response_model=schemas.Supplier)
def update_supplier(
    supplier_id: int,
    supplier_in: schemas.SupplierUpdate,
    db: Session = Depends(get_db),
) -> models.Supplier:
    supplier = crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    supplier = crud.update_supplier(db, supplier, supplier_in)
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)) -> Response:
    supplier = crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    crud.delete_supplier(db, supplier)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{supplier_id}/rates",
    response_model=schemas.SupplierRate,
    status_code=status.HTTP_201_CREATED,
)
def create_supplier_rate(
    supplier_id: int,
    rate_in: schemas.SupplierRateCreate,
    db: Session = Depends(get_db),
) -> models.SupplierRate:
    supplier = crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    rate = crud.create_supplier_rate(db, supplier, rate_in)
    db.refresh(rate)
    return rate


@router.get("/{supplier_id}/rates", response_model=List[schemas.SupplierRate])
def list_supplier_rates(supplier_id: int, db: Session = Depends(get_db)) -> List[models.SupplierRate]:
    supplier = crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return list(crud.list_supplier_rates(db, supplier))


@router.get("/{supplier_id}/rates/{rate_id}", response_model=schemas.SupplierRate)
def get_supplier_rate(
    supplier_id: int,
    rate_id: int,
    db: Session = Depends(get_db),
) -> models.SupplierRate:
    supplier = crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    rate = crud.get_supplier_rate(db, supplier, rate_id)
    if not rate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate not found")
    return rate


@router.put("/{supplier_id}/rates/{rate_id}", response_model=schemas.SupplierRate)
def update_supplier_rate(
    supplier_id: int,
    rate_id: int,
    rate_in: schemas.SupplierRateUpdate,
    db: Session = Depends(get_db),
) -> models.SupplierRate:
    supplier = crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    rate = crud.get_supplier_rate(db, supplier, rate_id)
    if not rate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate not found")
    rate = crud.update_supplier_rate(db, rate, rate_in)
    db.refresh(rate)
    return rate


@router.delete("/{supplier_id}/rates/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier_rate(supplier_id: int, rate_id: int, db: Session = Depends(get_db)) -> Response:
    supplier = crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    rate = crud.get_supplier_rate(db, supplier, rate_id)
    if not rate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rate not found")
    crud.delete_supplier_rate(db, rate)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/integrations/providers", response_model=List[schemas.SupplierIntegration])
def available_integrations() -> List[schemas.SupplierIntegration]:
    """Expose configured supplier integrations and supported resources."""
    integrations = get_available_supplier_integrations()
    return [
        schemas.SupplierIntegration(provider=provider, resources=resources)
        for provider, resources in integrations.items()
    ]


@router.get("/integrations/{provider}/{resource}")
def integration_inventory(
    provider: str,
    resource: str,
    query: Optional[str] = Query(None, description="Filter keyword such as city or code"),
) -> List[dict[str, str]]:
    """Return sample inventory payloads for external APIs to support itinerary planning."""
    try:
        return fetch_supplier_inventory(provider=provider, resource=resource, query=query)
    except ValueError as exc:  # surface validation issues as 400s
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


__all__ = ["router"]
