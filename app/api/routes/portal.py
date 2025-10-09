"""Client portal endpoints for traveler engagement."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ... import crud, models, schemas
from ...utils import render_portal_page
from ..deps import get_db

router = APIRouter(prefix="/portal", tags=["portal"])


@router.post(
    "/invitations",
    response_model=schemas.PortalAccessToken,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a traveler to review an itinerary via the client portal",
)
def create_portal_invitation(
    payload: schemas.PortalInvitationRequest, db: Session = Depends(get_db)
) -> schemas.PortalAccessToken:
    try:
        token = crud.create_portal_invitation(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.refresh(token)
    return token


def _get_token_or_error(db: Session, token: str) -> models.PortalAccessToken:
    portal_token = crud.get_portal_token(db, token)
    if not portal_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    if portal_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation expired")
    return portal_token


@router.get(
    "/invitations/{token}",
    response_model=schemas.PortalView,
    summary="Fetch the portal context for a traveler",
)
def get_portal_context(token: str, db: Session = Depends(get_db)) -> schemas.PortalView:
    portal_token = _get_token_or_error(db, token)
    crud.record_portal_view(db, portal_token)
    db.refresh(portal_token)
    return crud.get_portal_view(portal_token)


@router.get(
    "/invitations/{token}/page",
    response_class=HTMLResponse,
    summary="Render a mobile-friendly portal page for travelers",
)
def get_portal_page(token: str, db: Session = Depends(get_db)) -> str:
    portal_token = _get_token_or_error(db, token)
    crud.record_portal_view(db, portal_token)
    db.refresh(portal_token)
    view = crud.get_portal_view(portal_token)
    return render_portal_page(view, token)


@router.post(
    "/invitations/{token}/decision",
    response_model=schemas.PortalAccessToken,
    summary="Record traveler approval or decline of an itinerary",
)
def submit_portal_decision(
    token: str,
    payload: schemas.PortalDecisionRequest,
    db: Session = Depends(get_db),
) -> schemas.PortalAccessToken:
    portal_token = _get_token_or_error(db, token)
    updated = crud.apply_portal_decision(db, portal_token, payload)
    db.refresh(updated)
    return updated


@router.post(
    "/invitations/{token}/waiver",
    response_model=schemas.PortalAccessToken,
    summary="Allow travelers to sign or revoke waivers",
)
def submit_portal_waiver(
    token: str,
    payload: schemas.PortalWaiverRequest,
    db: Session = Depends(get_db),
) -> schemas.PortalAccessToken:
    portal_token = _get_token_or_error(db, token)
    updated = crud.update_portal_waiver(db, portal_token, payload)
    db.refresh(updated)
    return updated


@router.delete(
    "/invitations/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a traveler invitation",
)
def revoke_portal_invitation(token: str, db: Session = Depends(get_db)) -> Response:
    portal_token = crud.get_portal_token(db, token)
    if not portal_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    db.delete(portal_token)
    db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
