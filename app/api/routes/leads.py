"""CRM lead endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ... import crud, models, schemas
from ..deps import get_db

router = APIRouter(prefix="/leads", tags=["crm"])


@router.post("", response_model=schemas.Lead, status_code=status.HTTP_201_CREATED)
def create_lead(lead_in: schemas.LeadCreate, db: Session = Depends(get_db)) -> models.Lead:
    return crud.create_lead(db, lead_in)


@router.get("", response_model=List[schemas.Lead])
def list_leads(db: Session = Depends(get_db)) -> List[models.Lead]:
    return list(crud.list_leads(db))


@router.put("/{lead_id}", response_model=schemas.Lead)
def update_lead(
    lead_id: int,
    lead_in: schemas.LeadUpdate,
    db: Session = Depends(get_db),
) -> models.Lead:
    lead = crud.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return crud.update_lead(db, lead, lead_in)


@router.post("/{lead_id}/convert", response_model=schemas.LeadConversionResult)
def convert_lead(lead_id: int, db: Session = Depends(get_db)) -> schemas.LeadConversionResult:
    lead = crud.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    client = crud.convert_lead_to_client(db, lead)
    return schemas.LeadConversionResult(lead=lead, client=client)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: int, db: Session = Depends(get_db)) -> Response:
    lead = crud.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    crud.delete_lead(db, lead)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
