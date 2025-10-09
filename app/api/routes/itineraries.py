"""Itinerary management endpoints."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ... import crud, models, schemas
from ...utils import render_itinerary, render_travel_document
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
    itinerary = crud.create_itinerary(db, itinerary_in)
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
    itinerary = crud.update_itinerary(db, itinerary, itinerary_in)
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


@router.get(
    "/{itinerary_id}/pricing",
    response_model=schemas.PricingSummary,
    summary="Summarize itinerary pricing with margin insights",
)
def pricing_summary(itinerary_id: int, db: Session = Depends(get_db)) -> schemas.PricingSummary:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    return crud.get_pricing_summary(itinerary)


@router.get(
    "/{itinerary_id}/suggestions",
    response_model=List[schemas.ItinerarySuggestion],
    summary="AI-assisted suggestions for enriching an itinerary",
)
def itinerary_suggestions(
    itinerary_id: int,
    focus: Optional[str] = Query(None, description="Optional focus area such as pricing or wellness"),
    db: Session = Depends(get_db),
) -> List[schemas.ItinerarySuggestion]:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    return crud.build_itinerary_suggestions(itinerary, focus=focus)


@router.get(
    "/{itinerary_id}/documents/{document_type}",
    response_class=HTMLResponse,
    summary="Generate an auxiliary travel document",
)
def generate_travel_document(
    itinerary_id: int,
    document_type: str,
    db: Session = Depends(get_db),
) -> str:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    try:
        return render_travel_document(itinerary, document_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/{itinerary_id}/collaborators",
    response_model=schemas.ItineraryCollaborator,
    status_code=status.HTTP_201_CREATED,
)
def add_collaborator(
    itinerary_id: int,
    collaborator_in: schemas.ItineraryCollaboratorCreate,
    db: Session = Depends(get_db),
) -> models.ItineraryCollaborator:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    try:
        collaborator = crud.add_itinerary_collaborator(db, itinerary, collaborator_in)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.refresh(collaborator)
    return collaborator


@router.get(
    "/{itinerary_id}/collaborators",
    response_model=List[schemas.ItineraryCollaborator],
)
def list_collaborators(
    itinerary_id: int, db: Session = Depends(get_db)
) -> List[models.ItineraryCollaborator]:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    return list(crud.list_itinerary_collaborators(db, itinerary))


@router.post(
    "/{itinerary_id}/comments",
    response_model=schemas.ItineraryComment,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    itinerary_id: int,
    comment_in: schemas.ItineraryCommentCreate,
    db: Session = Depends(get_db),
) -> models.ItineraryComment:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    try:
        comment = crud.create_itinerary_comment(db, itinerary, comment_in)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.refresh(comment)
    return comment


@router.post(
    "/{itinerary_id}/comments/{comment_id}/resolve",
    response_model=schemas.ItineraryComment,
)
def resolve_comment(
    itinerary_id: int,
    comment_id: int,
    payload: schemas.CommentResolutionRequest,
    db: Session = Depends(get_db),
) -> models.ItineraryComment:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    comment = db.get(models.ItineraryComment, comment_id)
    if not comment or comment.itinerary_id != itinerary.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    updated = crud.set_comment_resolution(db, comment, payload.resolved)
    db.refresh(updated)
    return updated


@router.get(
    "/{itinerary_id}/versions",
    response_model=List[schemas.ItineraryVersion],
)
def list_versions(
    itinerary_id: int, db: Session = Depends(get_db)
) -> List[models.ItineraryVersion]:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    return list(crud.list_itinerary_versions(db, itinerary))
def print_itinerary(itinerary_id: int, db: Session = Depends(get_db)) -> str:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    return render_itinerary(itinerary)


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_itinerary(itinerary_id: int, db: Session = Depends(get_db)) -> Response:
    itinerary = crud.get_itinerary(db, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    crud.delete_itinerary(db, itinerary)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
