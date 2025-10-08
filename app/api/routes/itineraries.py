"""Itinerary management endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ... import crud, models, schemas
from ...utils import render_itinerary
from ..deps import get_db

router = APIRouter(prefix="/itineraries", tags=["itineraries"])


@router.post("", response_model=schemas.Itinerary, status_code=status.HTTP_201_CREATED)
def create_itinerary(
    itinerary_in: schemas.ItineraryCreate, db: Session = Depends(get_db)
) -> models.Itinerary:
    try:
        itinerary = crud.create_itinerary(db, itinerary_in)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.refresh(itinerary)
    return itinerary


@router.get("", response_model=List[schemas.Itinerary])
def list_itineraries(db: Session = Depends(get_db)) -> List[models.Itinerary]:
    return list(crud.list_itineraries(db))


@router.get("/{itinerary_id}", response_model=schemas.Itinerary)
def get_itinerary(itinerary_id: int, db: Session = Depends(get_db)) -> models.Itinerary:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    return itinerary


@router.put("/{itinerary_id}", response_model=schemas.Itinerary)
def update_itinerary(
    itinerary_id: int,
    itinerary_in: schemas.ItineraryUpdate,
    db: Session = Depends(get_db),
) -> models.Itinerary:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    try:
        itinerary = crud.update_itinerary(db, itinerary, itinerary_in)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.refresh(itinerary)
    return itinerary


@router.post(
    "/{itinerary_id}/duplicate",
    response_model=schemas.Itinerary,
    status_code=status.HTTP_201_CREATED,
    summary="Clone an existing itinerary to use as a template",
)
def duplicate_itinerary(itinerary_id: int, db: Session = Depends(get_db)) -> models.Itinerary:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    clone = crud.duplicate_itinerary(db, itinerary)
    db.refresh(clone)
    return clone


@router.post(
    "/{itinerary_id}/invoice",
    response_model=schemas.Invoice,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an invoice from an itinerary estimate",
)
def invoice_itinerary(
    itinerary_id: int,
    payload: schemas.ItineraryInvoiceCreate,
    db: Session = Depends(get_db),
) -> models.Invoice:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    invoice = crud.create_invoice_from_itinerary(db, itinerary, payload)
    db.refresh(invoice)
    return invoice


@router.get(
    "/{itinerary_id}/print",
    response_class=HTMLResponse,
    summary="Render a printable itinerary document",
)
def print_itinerary(
    itinerary_id: int,
    layout: str = Query("classic", description="Layout key such as classic, modern, gallery"),
    db: Session = Depends(get_db),
) -> str:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    return render_itinerary(itinerary, layout=layout)


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_itinerary(itinerary_id: int, db: Session = Depends(get_db)) -> Response:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    crud.delete_itinerary(db, itinerary)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
