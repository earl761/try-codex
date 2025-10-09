"""Endpoints for managing agency staff accounts."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.orm import Session

from ... import crud, schemas
from ...constants import ADMIN_ROLES
from ..deps import get_db

router = APIRouter(prefix="/agencies/{agency_id}/users", tags=["agency-users"])


def _get_agency_or_404(db: Session, agency_id: int) -> None:
    if not crud.get_travel_agency(db, agency_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")


@router.get("", response_model=list[schemas.User])
def list_agency_users(agency_id: int = Path(gt=0), db: Session = Depends(get_db)) -> list[schemas.User]:
    _get_agency_or_404(db, agency_id)
    users = crud.list_agency_users(db, agency_id)
    return [schemas.User.model_validate(user) for user in users]


@router.post("", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def create_agency_user(
    agency_id: int = Path(gt=0),
    payload: schemas.AgencyUserCreate = ...,  # noqa: B008
    db: Session = Depends(get_db),
) -> schemas.User:
    _get_agency_or_404(db, agency_id)
    if crud.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    derived_admin = (
        payload.is_admin if payload.is_admin is not None else payload.role in ADMIN_ROLES
    )
    user = crud.create_user(
        db,
        schemas.UserCreate(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            whatsapp_number=payload.whatsapp_number,
            agency_id=agency_id,
            is_active=payload.is_active,
            is_admin=derived_admin,
            is_super_admin=False,
            role=payload.role,
        ),
    )
    return schemas.User.model_validate(user)


@router.put("/{user_id}", response_model=schemas.User)
def update_agency_user(
    agency_id: int = Path(gt=0),
    user_id: int = Path(gt=0),
    payload: schemas.AgencyUserUpdate = ...,  # noqa: B008
    db: Session = Depends(get_db),
) -> schemas.User:
    _get_agency_or_404(db, agency_id)
    user = crud.get_user(db, user_id)
    if not user or user.agency_id != agency_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data: dict[str, object] = {}
    if payload.full_name is not None:
        update_data["full_name"] = payload.full_name
    if payload.whatsapp_number is not None:
        update_data["whatsapp_number"] = payload.whatsapp_number
    if payload.password is not None:
        update_data["password"] = payload.password
    if payload.role is not None:
        update_data["role"] = payload.role
        if payload.is_admin is None:
            update_data["is_admin"] = payload.role in ADMIN_ROLES
    if payload.is_active is not None:
        update_data["is_active"] = payload.is_active
    if payload.is_admin is not None:
        update_data["is_admin"] = payload.is_admin

    updated = crud.update_user(db, user, schemas.UserUpdate(**update_data))
    return schemas.User.model_validate(updated)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agency_user(
    agency_id: int = Path(gt=0),
    user_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> Response:
    _get_agency_or_404(db, agency_id)
    user = crud.get_user(db, user_id)
    if not user or user.agency_id != agency_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    crud.delete_user(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
