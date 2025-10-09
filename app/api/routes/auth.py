"""Authentication routes supporting signup, login, and two factor setup."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ... import crud, schemas
from ...constants import ADMIN_ROLES
from ..deps import get_db


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def signup(payload: schemas.SignupRequest, db: Session = Depends(get_db)) -> schemas.User:
    if crud.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    agency_id = payload.agency_id
    if payload.agency_name and not agency_id:
        agency = crud.create_travel_agency(
            db,
            schemas.TravelAgencyCreate(
                name=payload.agency_name,
                slug=None,
                contact_email=payload.email,
            ),
        )
        agency_id = agency.id
    elif agency_id:
        agency = crud.get_travel_agency(db, agency_id)
        if not agency:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")

    if payload.role:
        role = payload.role
    elif payload.agency_name and not payload.agency_id:
        role = "agency_owner"
    else:
        role = "staff"

    user = crud.create_user(
        db,
        schemas.UserCreate(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            whatsapp_number=payload.whatsapp_number,
            agency_id=agency_id,
            is_active=True,
            is_admin=role in ADMIN_ROLES,
            is_super_admin=False,
            role=role,
            is_admin=False,
        ),
    )
    return user


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)) -> schemas.LoginResponse:
    user, authenticated, requires_2fa = crud.authenticate_user(
        db, email=payload.email, password=payload.password, otp_code=payload.otp_code
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if requires_2fa and not authenticated:
        return schemas.LoginResponse(
            access_token="",
            token_type="bearer",
            user=schemas.User.model_validate(user),
            two_factor_required=True,
        )

    if not authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = secrets.token_urlsafe(32)
    crud.log_notification(
        db,
        event_type="user.login",
        channel="email",
        recipient=user.email,
        subject="Login successful",
        message="You have signed in to the Tour Planner dashboard.",
        metadata={"user_id": user.id},
        user=user,
    )
    return schemas.LoginResponse(access_token=token, user=schemas.User.model_validate(user))


@router.post("/2fa/setup", response_model=schemas.TwoFactorSetupResponse)
def setup_two_factor(
    payload: schemas.TwoFactorSetupRequest, db: Session = Depends(get_db)
) -> schemas.TwoFactorSetupResponse:
    user = crud.get_user_by_email(db, payload.email)
    if not user or not crud.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    secret, provisioning_uri = crud.initiate_two_factor(db, user)
    return schemas.TwoFactorSetupResponse(secret=secret, provisioning_uri=provisioning_uri)


@router.post("/2fa/activate", response_model=schemas.User)
def activate_two_factor(
    payload: schemas.TwoFactorVerifyRequest, db: Session = Depends(get_db)
) -> schemas.User:
    user = crud.get_user_by_email(db, payload.email)
    if not user or not crud.verify_two_factor_code(user, payload.otp_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")

    updated = crud.activate_two_factor(db, user)
    crud.log_notification(
        db,
        event_type="user.2fa.enabled",
        channel="email",
        recipient=user.email,
        subject="Two-factor authentication enabled",
        message="Two-factor authentication is now active on your account.",
        metadata={"user_id": user.id},
        user=updated,
    )
    return schemas.User.model_validate(updated)
