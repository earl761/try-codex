"""Reporting endpoints for operational insights."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ... import crud
from ..deps import get_db

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/itinerary-status")
def itinerary_status_report(db: Session = Depends(get_db)) -> dict[str, Any]:
    itineraries = list(crud.list_itineraries(db))
    statuses: dict[str, int] = {}
    for itinerary in itineraries:
        statuses[itinerary.status] = statuses.get(itinerary.status, 0) + 1
    return {"counts": statuses, "total": len(itineraries)}


@router.get("/sales")
def sales_report(db: Session = Depends(get_db)) -> dict[str, Any]:
    return crud.sales_report(db)
