"""CRUD helper functions used by the API routers."""
from __future__ import annotations

import json
import re
import secrets
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

import string

import pyotp
from passlib.context import CryptContext
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from . import models, schemas, utils
from .constants import (
    APP_NAME,
    DEFAULT_LANDING_PAGE,
    DEFAULT_POWERED_BY_LABEL,
    LANDING_PAGE_TEXT_FIELDS,
)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or secrets.token_hex(4)


def _ensure_unique_slug(session: Session, slug: str) -> str:
    base = slug
    counter = 1
    while session.scalar(select(models.TravelAgency).where(models.TravelAgency.slug == slug)):
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def _ensure_package_slug(session: Session, slug: str) -> str:
    base = slug
    counter = 1
    while session.scalar(
        select(models.SubscriptionPackage).where(models.SubscriptionPackage.slug == slug)
    ):
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def _coerce_powered_by_label(name: str, label: Optional[str]) -> str:
    candidate = (label or "").strip()
    if not candidate:
        candidate = f"{name} • {DEFAULT_POWERED_BY_LABEL}"
    elif APP_NAME.lower() not in candidate.lower():
        separator = " • " if "•" not in candidate else " "
        candidate = f"{candidate}{separator}{DEFAULT_POWERED_BY_LABEL}"
    return candidate


def _prepare_tags(tags: Optional[list[str] | str]) -> str | None:
    if tags is None:
        return None
    if isinstance(tags, str):
        values = [piece.strip() for piece in tags.split(",") if piece.strip()]
    else:
        values = [str(tag).strip() for tag in tags if str(tag).strip()]
    return ",".join(values) if values else None


def _prepare_features(features: Optional[list[str] | str]) -> str | None:
    return _prepare_tags(features)


def _prepare_modules(modules: Optional[list[str] | str]) -> list[str]:
    if modules is None:
        return ["core"]
    if isinstance(modules, str):
        values = [piece.strip().lower() for piece in modules.split(",") if piece.strip()]
    else:
        values = [str(module).strip().lower() for module in modules if str(module).strip()]
    normalized: list[str] = []
    for value in values or ["core"]:
        if value and value not in normalized:
            normalized.append(value)
    return normalized or ["core"]


def _media_assets_by_ids(
    session: Session, asset_ids: Sequence[int]
) -> dict[int, models.MediaAsset]:
    if not asset_ids:
        return {}
    statement = select(models.MediaAsset).where(models.MediaAsset.id.in_(asset_ids))
    assets = session.scalars(statement).unique().all()
    return {asset.id: asset for asset in assets}


def _generate_unique_pnr(session: Session) -> str:
    alphabet = "".join(ch for ch in string.ascii_uppercase if ch not in {"O", "I"})
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(6))
        exists = session.scalar(
            select(models.FlightBooking).where(models.FlightBooking.pnr == candidate)
        )
        if not exists:
            return candidate


def _notify_contact(
    session: Session,
    event_type: str,
    subject: str,
    message: str,
    *,
    email: str | None = None,
    phone: str | None = None,
    metadata: Optional[Dict[str, Any]] = None,
    user: Optional[models.User] = None,
) -> None:
    metadata_json = json.dumps(metadata or {})
    created = False
    if email:
        session.add(
            models.NotificationLog(
                event_type=event_type,
                channel="email",
                recipient=email,
                subject=subject,
                message=message,
                context=metadata_json,
                user=user,
            )
        )
        created = True
    if phone:
        session.add(
            models.NotificationLog(
                event_type=event_type,
                channel="whatsapp",
                recipient=phone,
                subject=subject,
                message=message,
                context=metadata_json,
                user=user,
            )
        )
        created = True
    if created:
        session.flush()


def log_notification(
    session: Session,
    *,
    event_type: str,
    channel: str,
    recipient: str,
    subject: str,
    message: str,
    status: str = "queued",
    metadata: Optional[Dict[str, Any]] = None,
    user: Optional[models.User] = None,
) -> models.NotificationLog:
    notification = models.NotificationLog(
        event_type=event_type,
        channel=channel,
        recipient=recipient,
        subject=subject,
        message=message,
        status=status,
        context=json.dumps(metadata or {}),
        user=user,
    )
    session.add(notification)
    session.flush()
    return notification


# Travel agency helpers


def create_travel_agency(session: Session, agency_in: schemas.TravelAgencyCreate) -> models.TravelAgency:
    data = agency_in.model_dump()
    slug = data.pop("slug") or _slugify(data["name"])
    data["slug"] = _ensure_unique_slug(session, slug)
    data["powered_by_label"] = _coerce_powered_by_label(
        data["name"], data.get("powered_by_label")
    )
    agency = models.TravelAgency(**data)
    session.add(agency)
    session.flush()
    _notify_contact(
        session,
        "agency.created",
        subject="Travel agency onboarded",
        message=f"Agency {agency.name} is now active on the platform.",
        email=agency.contact_email,
        phone=agency.contact_phone,
        metadata={"agency_id": agency.id},
    )
    return agency


def list_travel_agencies(session: Session) -> Sequence[models.TravelAgency]:
    statement = select(models.TravelAgency).order_by(models.TravelAgency.name)
    return session.scalars(statement).all()


def get_travel_agency(session: Session, agency_id: int) -> models.TravelAgency | None:
    return session.get(models.TravelAgency, agency_id)


def update_travel_agency(
    session: Session, agency: models.TravelAgency, agency_in: schemas.TravelAgencyUpdate
) -> models.TravelAgency:
    data = agency_in.model_dump(exclude_unset=True)
    if "name" in data and not data.get("slug"):
        data.setdefault("slug", _slugify(data["name"]))
    if "slug" in data:
        data["slug"] = _ensure_unique_slug(session, data["slug"])
    if "powered_by_label" in data or "name" in data:
        data["powered_by_label"] = _coerce_powered_by_label(
            data.get("name", agency.name),
            data.get("powered_by_label", agency.powered_by_label),
        )
    for field, value in data.items():
        setattr(agency, field, value)
    session.add(agency)
    session.flush()
    return agency


# Subscription package helpers


def create_subscription_package(
    session: Session, payload: schemas.SubscriptionPackageCreate
) -> models.SubscriptionPackage:
    data = payload.model_dump()
    slug = data.pop("slug", None) or _slugify(data["name"])
    data["slug"] = _ensure_package_slug(session, slug)
    data["features"] = _prepare_features(data.get("features"))
    data["modules"] = _prepare_modules(data.get("modules"))
    package = models.SubscriptionPackage(**data)
    session.add(package)
    session.flush()
    return package


def list_subscription_packages(
    session: Session, *, only_active: bool = False
) -> Sequence[models.SubscriptionPackage]:
    statement = select(models.SubscriptionPackage).order_by(models.SubscriptionPackage.price)
    if only_active:
        statement = statement.where(models.SubscriptionPackage.is_active.is_(True))
    return session.scalars(statement).unique().all()


def get_subscription_package(
    session: Session, package_id: int
) -> models.SubscriptionPackage | None:
    return session.get(models.SubscriptionPackage, package_id)


def update_subscription_package(
    session: Session,
    package: models.SubscriptionPackage,
    payload: schemas.SubscriptionPackageUpdate,
) -> models.SubscriptionPackage:
    data = payload.model_dump(exclude_unset=True)
    features = data.pop("features", None)
    modules = data.pop("modules", None)
    if "name" in data and not data.get("slug"):
        data.setdefault("slug", _slugify(data["name"]))
    if "slug" in data:
        data["slug"] = _ensure_package_slug(session, data["slug"])
    if features is not None:
        package.features = _prepare_features(features)
    if modules is not None:
        package.modules = _prepare_modules(modules)
    for field, value in data.items():
        setattr(package, field, value)
    session.add(package)
    session.flush()
    return package


def list_agency_subscriptions(
    session: Session, *, agency_id: int | None = None
) -> Sequence[models.AgencySubscription]:
    statement = select(models.AgencySubscription).options(
        selectinload(models.AgencySubscription.package),
        selectinload(models.AgencySubscription.agency),
    )
    if agency_id is not None:
        statement = statement.where(models.AgencySubscription.agency_id == agency_id)
    statement = statement.order_by(models.AgencySubscription.created_at.desc())
    return session.scalars(statement).unique().all()


def agency_has_module(session: Session, agency_id: int, module: str) -> bool:
    desired = module.lower()
    statement = (
        select(models.AgencySubscription)
        .options(selectinload(models.AgencySubscription.package))
        .where(
            models.AgencySubscription.agency_id == agency_id,
            models.AgencySubscription.status == "active",
        )
    )
    for subscription in session.scalars(statement).unique().all():
        package = subscription.package
        modules = (package.modules if package and package.modules is not None else [])
        normalized = [str(value).lower() for value in modules]
        if desired in normalized:
            return True
    return False


def get_agency_subscription(
    session: Session, subscription_id: int
) -> models.AgencySubscription | None:
    statement = (
        select(models.AgencySubscription)
        .options(
            selectinload(models.AgencySubscription.package),
            selectinload(models.AgencySubscription.agency),
        )
        .where(models.AgencySubscription.id == subscription_id)
    )
    return session.scalars(statement).unique().first()


def create_agency_subscription(
    session: Session, payload: schemas.AgencySubscriptionCreate
) -> models.AgencySubscription:
    data = payload.model_dump()
    if not data.get("start_date"):
        data["start_date"] = date.today()
    subscription = models.AgencySubscription(**data)
    session.add(subscription)
    session.flush()
    agency = session.get(models.TravelAgency, subscription.agency_id)
    package = session.get(models.SubscriptionPackage, subscription.package_id)
    if agency and package:
        _notify_contact(
            session,
            "subscription.created",
            subject="Subscription activated",
            message=f"{agency.name} subscribed to {package.name}.",
            email=agency.contact_email,
            phone=agency.contact_phone,
            metadata={
                "agency_id": subscription.agency_id,
                "package_id": subscription.package_id,
                "subscription_id": subscription.id,
            },
        )
    return subscription


def update_agency_subscription(
    session: Session,
    subscription: models.AgencySubscription,
    payload: schemas.AgencySubscriptionUpdate,
) -> models.AgencySubscription:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(subscription, field, value)
    session.add(subscription)
    session.flush()
    agency = session.get(models.TravelAgency, subscription.agency_id)
    package = session.get(models.SubscriptionPackage, subscription.package_id)
    if agency and package:
        _notify_contact(
            session,
            "subscription.updated",
            subject="Subscription updated",
            message=f"Subscription for {agency.name} now {subscription.status}.",
            email=agency.contact_email,
            phone=agency.contact_phone,
            metadata={
                "agency_id": subscription.agency_id,
                "package_id": subscription.package_id,
                "subscription_id": subscription.id,
            },
        )
    return subscription


# Media helpers


def create_media_asset(
    session: Session,
    *,
    filename: str,
    content_type: str,
    original_path: str,
    optimized_path: str,
    width: int | None = None,
    height: int | None = None,
    file_size: int | None = None,
    agency_id: int | None = None,
    uploaded_by_id: int | None = None,
    alt_text: str | None = None,
    tags: list[str] | str | None = None,
) -> models.MediaAsset:
    asset = models.MediaAsset(
        filename=filename,
        content_type=content_type,
        original_path=original_path,
        optimized_path=optimized_path,
        width=width,
        height=height,
        file_size=file_size,
        agency_id=agency_id,
        uploaded_by_id=uploaded_by_id,
        alt_text=alt_text,
        tags=_prepare_tags(tags),
    )
    session.add(asset)
    session.flush()
    return asset


def list_media_assets(session: Session) -> Sequence[models.MediaAsset]:
    statement = select(models.MediaAsset).order_by(models.MediaAsset.created_at.desc())
    return session.scalars(statement).unique().all()


def get_media_asset(session: Session, asset_id: int) -> models.MediaAsset | None:
    statement = select(models.MediaAsset).where(models.MediaAsset.id == asset_id)
    return session.scalars(statement).unique().first()


def update_media_asset(
    session: Session, asset: models.MediaAsset, payload: schemas.MediaAssetUpdate
) -> models.MediaAsset:
    data = payload.model_dump(exclude_unset=True)
    tags = data.pop("tags", None)
    if tags is not None:
        asset.tags = _prepare_tags(tags)
    for field, value in data.items():
        setattr(asset, field, value)
    session.add(asset)
    session.flush()
    return asset


def delete_media_asset(session: Session, asset: models.MediaAsset) -> None:
    utils.remove_media_files(asset)
    session.delete(asset)
    session.flush()


# User helpers


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_user(session: Session, user_in: schemas.UserCreate) -> models.User:
    user = models.User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        whatsapp_number=user_in.whatsapp_number,
        agency_id=user_in.agency_id,
        is_active=user_in.is_active,
        is_admin=user_in.is_admin,
        is_super_admin=user_in.is_super_admin,
    )
    session.add(user)
    session.flush()
    _notify_contact(
        session,
        "user.registered",
        subject="Welcome to Tour Planner",
        message="Your user account has been created successfully.",
        email=user.email,
        phone=user.whatsapp_number,
        metadata={"user_id": user.id},
        user=user,
    )
    return user


def get_user(session: Session, user_id: int) -> models.User | None:
    return session.get(models.User, user_id)


def get_user_by_email(session: Session, email: str) -> models.User | None:
    statement = select(models.User).where(models.User.email == email)
    return session.scalars(statement).first()


def update_user(session: Session, user: models.User, user_in: schemas.UserUpdate) -> models.User:
    data = user_in.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    for field, value in data.items():
        setattr(user, field, value)
    if password:
        user.hashed_password = hash_password(password)
    session.add(user)
    session.flush()
    return user


def authenticate_user(
    session: Session, *, email: str, password: str, otp_code: str | None = None
) -> tuple[models.User | None, bool, bool]:
    user = get_user_by_email(session, email)
    if not user or not user.is_active:
        return None, False, False
    if not verify_password(password, user.hashed_password):
        return None, False, False
    if user.two_factor_enabled:
        if not otp_code:
            return user, False, True
        if not verify_two_factor_code(user, otp_code):
            return None, False, True
    return user, True, user.two_factor_enabled


def initiate_two_factor(session: Session, user: models.User) -> tuple[str, str]:
    secret = pyotp.random_base32()
    user.two_factor_secret = secret
    session.add(user)
    session.flush()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name="Tour Planner")
    log_notification(
        session,
        event_type="user.2fa.setup",
        channel="email",
        recipient=user.email,
        subject="2FA setup initiated",
        message="Use the provided secret to configure your authenticator app.",
        metadata={"user_id": user.id},
        user=user,
    )
    return secret, provisioning_uri


def verify_two_factor_code(user: models.User, otp_code: str) -> bool:
    if not user.two_factor_secret:
        return False
    totp = pyotp.TOTP(user.two_factor_secret)
    return bool(totp.verify(otp_code, valid_window=1))


def activate_two_factor(session: Session, user: models.User) -> models.User:
    user.two_factor_enabled = True
    session.add(user)
    session.flush()
    return user


def deactivate_two_factor(session: Session, user: models.User) -> models.User:
    user.two_factor_enabled = False
    user.two_factor_secret = None
    session.add(user)
    session.flush()
    return user


# Client helpers


def create_client(session: Session, client_in: schemas.ClientCreate) -> models.Client:
    client = models.Client(**client_in.model_dump())
    session.add(client)
    session.flush()
    _notify_contact(
        session,
        "client.created",
        subject="Client profile created",
        message=f"Welcome aboard {client.name}.",
        email=client.email,
        phone=client.phone,
        metadata={"client_id": client.id},
    )
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
    _notify_contact(
        session,
        "client.updated",
        subject="Client profile updated",
        message=f"Client {client.name} profile information has changed.",
        email=client.email,
        phone=client.phone,
        metadata={"client_id": client.id},
    )
    return client


def delete_client(session: Session, client: models.Client) -> None:
    session.delete(client)
    session.flush()


# Lead helpers


def create_lead(session: Session, lead_in: schemas.LeadCreate) -> models.Lead:
    lead = models.Lead(**lead_in.model_dump())
    session.add(lead)
    session.flush()
    _notify_contact(
        session,
        "lead.created",
        subject="New lead captured",
        message=f"Lead {lead.name} has been captured.",
        email=lead.email,
        metadata={"lead_id": lead.id},
    )
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
        "agency_id": lead.agency_id,
    }
    client = models.Client(**{key: value for key, value in client_data.items() if value is not None})
    session.add(client)
    session.flush()

    lead.client_id = client.id
    lead.status = "converted"
    session.add(lead)
    session.flush()

    _notify_contact(
        session,
        "lead.converted",
        subject="Lead converted",
        message=f"Lead {lead.name} has been converted to a client.",
        email=lead.email,
        metadata={"lead_id": lead.id, "client_id": client.id},
    )
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


def _calculate_itinerary_cost(itinerary: models.Itinerary) -> Decimal:
    total = Decimal("0")
    for item in itinerary.items:
        if item.estimated_cost is not None:
            total += Decimal(item.estimated_cost)
    for extension in itinerary.extensions:
        if extension.additional_cost is not None:
            total += Decimal(extension.additional_cost)
    return total


def _apply_pricing_strategy(itinerary: models.Itinerary) -> None:
    base_cost = _calculate_itinerary_cost(itinerary)
    strategy = (itinerary.markup_strategy or "flat").lower()
    target = itinerary.target_margin or Decimal("0")
    if not isinstance(target, Decimal):
        target = Decimal(str(target))

    markup_value = Decimal("0")
    if strategy == "percentage":
        markup_value = (base_cost * target / Decimal("100")).quantize(Decimal("0.01"))
    else:
        markup_value = Decimal(target).quantize(Decimal("0.01")) if target else Decimal("0")

    if itinerary.total_price is None or itinerary.total_price < base_cost:
        itinerary.total_price = (base_cost + markup_value).quantize(Decimal("0.01"))

    itinerary.calculated_margin = (Decimal(itinerary.total_price or 0) - base_cost).quantize(
        Decimal("0.01")
    )

    if itinerary.estimate_amount is None and itinerary.total_price is not None:
        itinerary.estimate_amount = itinerary.total_price


def get_pricing_summary(itinerary: models.Itinerary) -> schemas.PricingSummary:
    base_cost = _calculate_itinerary_cost(itinerary)
    total_price = Decimal(itinerary.total_price or itinerary.estimate_amount or 0)
    markup_value = total_price - base_cost
    margin_percent = float(0)
    if base_cost:
        margin_percent = float((markup_value / base_cost) * Decimal("100"))
    return schemas.PricingSummary(
        base_cost=base_cost.quantize(Decimal("0.01")),
        markup_value=markup_value.quantize(Decimal("0.01")),
        total_price=total_price.quantize(Decimal("0.01")) if total_price else Decimal("0.00"),
        margin_percent=round(margin_percent, 2),
    )


def create_itinerary(session: Session, itinerary_in: schemas.ItineraryCreate) -> models.Itinerary:
    payload = itinerary_in.model_dump()
    items_data = payload.pop("items", [])
    extensions_data = payload.pop("extensions", [])
    notes_data = payload.pop("notes", [])

    asset_ids = {
        media["asset_id"]
        for item in items_data
        for media in item.get("media", [])
    }
    asset_map = _media_assets_by_ids(session, list(asset_ids))
    missing_assets = asset_ids - set(asset_map.keys())
    if missing_assets:
        raise ValueError(f"Unknown media asset ids: {sorted(missing_assets)}")

    itinerary = models.Itinerary(**payload)
    session.add(itinerary)

    for item_data in items_data:
        media_payloads = item_data.pop("media", [])
        itinerary_item = models.ItineraryItem(**item_data)
        for media_payload in media_payloads:
            asset = asset_map[media_payload["asset_id"]]
            itinerary_item.media_links.append(
                models.ItineraryItemMedia(
                    asset=asset,
                    usage=media_payload.get("usage", "gallery"),
                )
            )
        itinerary.items.append(itinerary_item)

    for extension in extensions_data:
        itinerary.extensions.append(models.ItineraryExtension(**extension))

    for note in notes_data:
        itinerary.notes.append(models.ItineraryNote(**note))

    session.add(itinerary)
    session.flush()

    _apply_pricing_strategy(itinerary)

    record_itinerary_version(
        session,
        itinerary,
        schemas.ItineraryVersionCreate(
            summary="Initial draft",
            snapshot={
                "status": itinerary.status,
                "estimate_amount": str(itinerary.estimate_amount)
                if itinerary.estimate_amount
                else None,
                "total_price": str(itinerary.total_price) if itinerary.total_price else None,
            },
        ),
    )

    client = itinerary.client
    _notify_contact(
        session,
        "itinerary.created",
        subject="New itinerary created",
        message=f"Itinerary {itinerary.title} has been created.",
        email=client.email if client else None,
        phone=client.phone if client else None,
        metadata={"itinerary_id": itinerary.id},
    )
    return itinerary


def list_itineraries(session: Session) -> Sequence[models.Itinerary]:
    statement = (
        select(models.Itinerary)
        .options(
            selectinload(models.Itinerary.items)
            .selectinload(models.ItineraryItem.media_links)
            .selectinload(models.ItineraryItemMedia.asset),
            selectinload(models.Itinerary.client),
            selectinload(models.Itinerary.tour_package),
            selectinload(models.Itinerary.extensions),
            selectinload(models.Itinerary.notes),
            selectinload(models.Itinerary.collaborators).selectinload(
                models.ItineraryCollaborator.user
            ),
            selectinload(models.Itinerary.comments).selectinload(
                models.ItineraryComment.author
            ),
            selectinload(models.Itinerary.versions),
        )
        .order_by(models.Itinerary.start_date)
    )
    return session.scalars(statement).unique().all()


def get_itinerary(session: Session, itinerary_id: int) -> models.Itinerary | None:
    statement = (
        select(models.Itinerary)
        .where(models.Itinerary.id == itinerary_id)
        .options(
            selectinload(models.Itinerary.items)
            .selectinload(models.ItineraryItem.media_links)
            .selectinload(models.ItineraryItemMedia.asset),
            selectinload(models.Itinerary.client),
            selectinload(models.Itinerary.tour_package),
            selectinload(models.Itinerary.extensions),
            selectinload(models.Itinerary.notes),
            selectinload(models.Itinerary.collaborators).selectinload(
                models.ItineraryCollaborator.user
            ),
            selectinload(models.Itinerary.comments).selectinload(
                models.ItineraryComment.author
            ),
            selectinload(models.Itinerary.versions),
            selectinload(models.Itinerary.portal_tokens),
        )
    )
    return session.scalars(statement).unique().first()


def update_itinerary(
    session: Session, itinerary: models.Itinerary, itinerary_in: schemas.ItineraryUpdate
) -> models.Itinerary:
    data = itinerary_in.model_dump(exclude_unset=True)
    items_data = data.pop("items", None)
    extensions_data = data.pop("extensions", None)
    notes_data = data.pop("notes", None)

    for field, value in data.items():
        setattr(itinerary, field, value)

    if items_data is not None:
        itinerary.items.clear()
        session.flush()
        asset_ids = {
            media["asset_id"]
            for item in items_data
            for media in item.get("media", [])
        }
        asset_map = _media_assets_by_ids(session, list(asset_ids))
        missing_assets = asset_ids - set(asset_map.keys())
        if missing_assets:
            raise ValueError(f"Unknown media asset ids: {sorted(missing_assets)}")
        for item_data in items_data:
            media_payloads = item_data.pop("media", [])
            itinerary_item = models.ItineraryItem(**item_data)
            for media_payload in media_payloads:
                asset = asset_map[media_payload["asset_id"]]
                itinerary_item.media_links.append(
                    models.ItineraryItemMedia(
                        asset=asset,
                        usage=media_payload.get("usage", "gallery"),
                    )
                )
            itinerary.items.append(itinerary_item)

    if extensions_data is not None:
        itinerary.extensions.clear()
        for extension in extensions_data:
            itinerary.extensions.append(models.ItineraryExtension(**extension))

    if notes_data is not None:
        itinerary.notes.clear()
        for note in notes_data:
            itinerary.notes.append(models.ItineraryNote(**note))

    session.add(itinerary)
    session.flush()

    _apply_pricing_strategy(itinerary)

    record_itinerary_version(
        session,
        itinerary,
        schemas.ItineraryVersionCreate(
            summary=f"Updated on {datetime.utcnow():%Y-%m-%d %H:%M UTC}",
            snapshot={
                "status": itinerary.status,
                "estimate_amount": str(itinerary.estimate_amount)
                if itinerary.estimate_amount
                else None,
                "total_price": str(itinerary.total_price) if itinerary.total_price else None,
            },
        ),
    )

    client = itinerary.client
    _notify_contact(
        session,
        "itinerary.updated",
        subject="Itinerary updated",
        message=f"Itinerary {itinerary.title} has been updated.",
        email=client.email if client else None,
        phone=client.phone if client else None,
        metadata={"itinerary_id": itinerary.id},
    )
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
        estimate_amount=itinerary.estimate_amount,
        estimate_currency=itinerary.estimate_currency,
        brand_logo_url=itinerary.brand_logo_url,
        brand_primary_color=itinerary.brand_primary_color,
        brand_secondary_color=itinerary.brand_secondary_color,
        brand_footer_note=itinerary.brand_footer_note,
    )
    session.add(clone)
    session.flush()

    for item in itinerary.items:
        clone_item = models.ItineraryItem(
            day_number=item.day_number,
            title=item.title,
            description=item.description,
            location=item.location,
            start_time=item.start_time,
            end_time=item.end_time,
            category=item.category,
            supplier_reference=item.supplier_reference,
            estimated_cost=item.estimated_cost,
            estimated_currency=item.estimated_currency,
        )
        for link in item.media_links:
            clone_item.media_links.append(
                models.ItineraryItemMedia(
                    media_asset_id=link.media_asset_id,
                    usage=link.usage,
                )
            )
        clone.items.append(clone_item)

    for extension in itinerary.extensions:
        clone.extensions.append(
            models.ItineraryExtension(
                title=extension.title,
                description=extension.description,
                additional_cost=extension.additional_cost,
                currency=extension.currency,
            )
        )

    for note in itinerary.notes:
        clone.notes.append(
            models.ItineraryNote(
                category=note.category,
                title=note.title,
                content=note.content,
            )
        )

    session.add(clone)
    session.flush()

    client = clone.client
    _notify_contact(
        session,
        "itinerary.duplicated",
        subject="Itinerary duplicated",
        message=f"A copy of itinerary {itinerary.title} is ready for review.",
        email=client.email if client else None,
        phone=client.phone if client else None,
        metadata={"original_itinerary_id": itinerary.id, "clone_itinerary_id": clone.id},
    )
    return clone


def add_itinerary_collaborator(
    session: Session,
    itinerary: models.Itinerary,
    collaborator_in: schemas.ItineraryCollaboratorCreate,
) -> models.ItineraryCollaborator:
    user = session.get(models.User, collaborator_in.user_id)
    if not user:
        raise ValueError("Unknown user provided for collaboration")
    existing = session.scalar(
        select(models.ItineraryCollaborator)
        .where(models.ItineraryCollaborator.itinerary_id == itinerary.id)
        .where(models.ItineraryCollaborator.user_id == collaborator_in.user_id)
    )
    if existing:
        return existing
    collaborator = models.ItineraryCollaborator(
        itinerary=itinerary,
        user=user,
        role=collaborator_in.role,
        permissions=collaborator_in.permissions,
    )
    session.add(collaborator)
    session.flush()
    return collaborator


def list_itinerary_collaborators(
    session: Session, itinerary: models.Itinerary
) -> Sequence[models.ItineraryCollaborator]:
    statement = (
        select(models.ItineraryCollaborator)
        .where(models.ItineraryCollaborator.itinerary_id == itinerary.id)
        .options(selectinload(models.ItineraryCollaborator.user))
        .order_by(models.ItineraryCollaborator.created_at)
    )
    return session.scalars(statement).all()


def create_itinerary_comment(
    session: Session,
    itinerary: models.Itinerary,
    comment_in: schemas.ItineraryCommentCreate,
) -> models.ItineraryComment:
    if comment_in.author_id and not session.get(models.User, comment_in.author_id):
        raise ValueError("Unknown comment author")
    comment = models.ItineraryComment(
        itinerary=itinerary,
        author_id=comment_in.author_id,
        body=comment_in.body,
    )
    session.add(comment)
    session.flush()
    return comment


def set_comment_resolution(
    session: Session, comment: models.ItineraryComment, resolved: bool
) -> models.ItineraryComment:
    comment.resolved = resolved
    session.add(comment)
    session.flush()
    return comment


def record_itinerary_version(
    session: Session,
    itinerary: models.Itinerary,
    version_in: schemas.ItineraryVersionCreate,
) -> models.ItineraryVersion:
    latest_number = session.scalar(
        select(models.ItineraryVersion.version_number)
        .where(models.ItineraryVersion.itinerary_id == itinerary.id)
        .order_by(desc(models.ItineraryVersion.version_number))
    )
    version = models.ItineraryVersion(
        itinerary=itinerary,
        version_number=(latest_number or 0) + 1,
        summary=version_in.summary,
        snapshot=version_in.snapshot or {},
    )
    session.add(version)
    session.flush()
    return version


def list_itinerary_versions(
    session: Session, itinerary: models.Itinerary
) -> Sequence[models.ItineraryVersion]:
    statement = (
        select(models.ItineraryVersion)
        .where(models.ItineraryVersion.itinerary_id == itinerary.id)
        .order_by(desc(models.ItineraryVersion.version_number))
    )
    return session.scalars(statement).all()


def build_itinerary_suggestions(
    itinerary: models.Itinerary, focus: Optional[str] = None
) -> list[schemas.ItinerarySuggestion]:
    suggestions = utils.generate_itinerary_suggestions(itinerary, focus=focus)
    return [schemas.ItinerarySuggestion(**suggestion) for suggestion in suggestions]


def create_portal_invitation(
    session: Session, payload: schemas.PortalInvitationRequest
) -> models.PortalAccessToken:
    itinerary = get_itinerary(session, payload.itinerary_id)
    if not itinerary:
        raise ValueError("Itinerary not found")
    client = session.get(models.Client, payload.client_id)
    if not client:
        raise ValueError("Client not found")
    if itinerary.client_id != client.id:
        raise ValueError("Client must match itinerary client")
    token = secrets.token_urlsafe(24)
    portal_token = models.PortalAccessToken(
        itinerary=itinerary,
        client=client,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=payload.expires_in_days),
        status="pending",
    )
    session.add(portal_token)
    session.flush()
    return portal_token


def get_portal_token(session: Session, token: str) -> models.PortalAccessToken | None:
    statement = (
        select(models.PortalAccessToken)
        .where(models.PortalAccessToken.token == token)
        .options(
            selectinload(models.PortalAccessToken.itinerary)
            .selectinload(models.Itinerary.items)
            .selectinload(models.ItineraryItem.media_links)
            .selectinload(models.ItineraryItemMedia.asset),
            selectinload(models.PortalAccessToken.itinerary)
            .selectinload(models.Itinerary.notes),
            selectinload(models.PortalAccessToken.itinerary)
            .selectinload(models.Itinerary.extensions),
            selectinload(models.PortalAccessToken.itinerary).selectinload(
                models.Itinerary.client
            ),
        )
    )
    return session.scalars(statement).first()


def record_portal_view(
    session: Session, portal_token: models.PortalAccessToken
) -> models.PortalAccessToken:
    portal_token.last_viewed_at = datetime.utcnow()
    session.add(portal_token)
    session.flush()
    return portal_token


def apply_portal_decision(
    session: Session,
    portal_token: models.PortalAccessToken,
    decision: schemas.PortalDecisionRequest,
) -> models.PortalAccessToken:
    portal_token.status = decision.decision
    portal_token.approved_at = datetime.utcnow() if decision.decision == "approved" else None
    portal_token.approval_notes = decision.notes
    session.add(portal_token)
    session.flush()
    return portal_token


def update_portal_waiver(
    session: Session, portal_token: models.PortalAccessToken, waiver: schemas.PortalWaiverRequest
) -> models.PortalAccessToken:
    portal_token.waiver_signed = waiver.accepted
    session.add(portal_token)
    session.flush()
    return portal_token


def get_portal_view(portal_token: models.PortalAccessToken) -> schemas.PortalView:
    itinerary = portal_token.itinerary
    pricing = get_pricing_summary(itinerary)
    agency = itinerary.client.agency if itinerary.client else None
    branding = {
        "agency_name": agency.name if agency else None,
        "logo": itinerary.brand_logo_url or getattr(agency, "logo_url", None),
        "primary_color": itinerary.brand_primary_color
        or getattr(agency, "brand_primary_color", None),
        "powered_by": (agency.powered_by_label if agency else None)
        or DEFAULT_POWERED_BY_LABEL,
    }
    available_documents = ["travel_brief", "visa_letter", "waiver"]
    return schemas.PortalView(
        itinerary=itinerary,
        pricing=pricing,
        available_documents=available_documents,
        payment_methods=list(utils.SUPPORTED_PAYMENT_PROVIDERS.keys()),
        branding=branding,
    )


# Finance helpers


def create_invoice(session: Session, invoice_in: schemas.InvoiceCreate) -> models.Invoice:
    invoice = models.Invoice(**invoice_in.model_dump())
    session.add(invoice)
    session.flush()
    client = invoice.client
    _notify_contact(
        session,
        "invoice.created",
        subject="Invoice generated",
        message=f"Invoice #{invoice.id} has been generated for your trip.",
        email=client.email if client else None,
        phone=client.phone if client else None,
        metadata={"invoice_id": invoice.id},
    )
    return invoice


def create_invoice_from_itinerary(
    session: Session,
    itinerary: models.Itinerary,
    payload: schemas.ItineraryInvoiceCreate,
) -> models.Invoice:
    data = payload.model_dump()
    amount = data.get("amount")
    if amount is None:
        amount = itinerary.estimate_amount or itinerary.total_price or Decimal("0")
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    currency = data.get("currency")
    if currency is None:
        currency = (
            itinerary.estimate_currency
            or (itinerary.client.agency.default_currency if itinerary.client and itinerary.client.agency else None)
            or "USD"
        )

    invoice = models.Invoice(
        client_id=itinerary.client_id,
        itinerary_id=itinerary.id,
        issue_date=data["issue_date"],
        due_date=data["due_date"],
        amount=amount,
        currency=currency,
    )
    session.add(invoice)
    session.flush()

    client = itinerary.client
    message = f"Your itinerary {itinerary.title} estimate has been issued."
    if data.get("notes"):
        message += f" Notes: {data['notes']}"
    _notify_contact(
        session,
        "itinerary.invoice_created",
        subject="Itinerary estimate ready",
        message=message,
        email=client.email if client else None,
        phone=client.phone if client else None,
        metadata={"itinerary_id": itinerary.id, "invoice_id": invoice.id},
    )
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
    invoice = payment.invoice
    client = invoice.client if invoice else None
    _notify_contact(
        session,
        "payment.recorded",
        subject="Payment received",
        message=f"Payment of {payment.amount} {payment.currency} has been recorded.",
        email=client.email if client else None,
        phone=client.phone if client else None,
        metadata={"invoice_id": invoice.id if invoice else None, "payment_id": payment.id},
    )
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


def create_payment_gateway(
    session: Session, payload: schemas.PaymentGatewayCreate
) -> models.PaymentGateway:
    gateway = models.PaymentGateway(**payload.model_dump())
    session.add(gateway)
    session.flush()
    return gateway


def list_payment_gateways(session: Session) -> Sequence[models.PaymentGateway]:
    statement = select(models.PaymentGateway).order_by(models.PaymentGateway.created_at.desc())
    return session.scalars(statement).all()


def get_payment_gateway(session: Session, gateway_id: int) -> models.PaymentGateway | None:
    return session.get(models.PaymentGateway, gateway_id)


def update_payment_gateway(
    session: Session, gateway: models.PaymentGateway, payload: schemas.PaymentGatewayUpdate
) -> models.PaymentGateway:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(gateway, field, value)
    session.add(gateway)
    session.flush()
    return gateway


def delete_payment_gateway(session: Session, gateway: models.PaymentGateway) -> None:
    session.delete(gateway)
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


# Supplier helpers


def create_supplier(session: Session, supplier_in: schemas.SupplierCreate) -> models.Supplier:
    supplier = models.Supplier(**supplier_in.model_dump())
    session.add(supplier)
    session.flush()
    _notify_contact(
        session,
        "supplier.created",
        subject="Supplier joined",
        message=f"Supplier {supplier.name} has been onboarded.",
        email=supplier.contact_email,
        phone=supplier.contact_phone,
        metadata={"supplier_id": supplier.id},
    )
    return supplier


def list_suppliers(session: Session) -> Sequence[models.Supplier]:
    statement = select(models.Supplier).options(selectinload(models.Supplier.rates)).order_by(
        models.Supplier.name
    )
    return session.scalars(statement).unique().all()


def get_supplier(session: Session, supplier_id: int) -> models.Supplier | None:
    statement = (
        select(models.Supplier)
        .where(models.Supplier.id == supplier_id)
        .options(selectinload(models.Supplier.rates))
    )
    return session.scalars(statement).unique().first()


def update_supplier(
    session: Session, supplier: models.Supplier, supplier_in: schemas.SupplierUpdate
) -> models.Supplier:
    for field, value in supplier_in.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    session.add(supplier)
    session.flush()
    return supplier


def delete_supplier(session: Session, supplier: models.Supplier) -> None:
    session.delete(supplier)
    session.flush()


def create_supplier_rate(
    session: Session, supplier: models.Supplier, rate_in: schemas.SupplierRateCreate
) -> models.SupplierRate:
    rate = models.SupplierRate(supplier_id=supplier.id, **rate_in.model_dump())
    session.add(rate)
    session.flush()
    _notify_contact(
        session,
        "supplier.rate_created",
        subject="Supplier rate published",
        message=f"A new rate '{rate.title}' is available from {supplier.name}.",
        email=supplier.contact_email,
        phone=supplier.contact_phone,
        metadata={"supplier_id": supplier.id, "rate_id": rate.id},
    )
    return rate


def list_supplier_rates(session: Session, supplier: models.Supplier) -> Sequence[models.SupplierRate]:
    statement = (
        select(models.SupplierRate)
        .where(models.SupplierRate.supplier_id == supplier.id)
        .order_by(models.SupplierRate.title)
    )
    return session.scalars(statement).all()


def get_supplier_rate(
    session: Session, supplier: models.Supplier, rate_id: int
) -> models.SupplierRate | None:
    statement = (
        select(models.SupplierRate)
        .where(
            models.SupplierRate.supplier_id == supplier.id,
            models.SupplierRate.id == rate_id,
        )
    )
    return session.scalars(statement).first()


def update_supplier_rate(
    session: Session,
    rate: models.SupplierRate,
    rate_in: schemas.SupplierRateUpdate,
) -> models.SupplierRate:
    for field, value in rate_in.model_dump(exclude_unset=True).items():
        setattr(rate, field, value)
    session.add(rate)
    session.flush()
    return rate


def delete_supplier_rate(session: Session, rate: models.SupplierRate) -> None:
    session.delete(rate)
    session.flush()


# Integration helpers


def create_integration_credential(
    session: Session, credential_in: schemas.IntegrationCredentialCreate
) -> models.IntegrationCredential:
    credential = models.IntegrationCredential(**credential_in.model_dump())
    session.add(credential)
    session.flush()
    _notify_contact(
        session,
        "integration.credential_created",
        subject="Integration key stored",
        message=f"An API key for {credential.provider} has been configured.",
        metadata={"agency_id": credential.agency_id, "provider": credential.provider},
    )
    return credential


def list_integration_credentials(session: Session) -> Sequence[models.IntegrationCredential]:
    statement = select(models.IntegrationCredential).order_by(models.IntegrationCredential.provider)
    return session.scalars(statement).all()


def get_integration_credential(
    session: Session, credential_id: int
) -> models.IntegrationCredential | None:
    return session.get(models.IntegrationCredential, credential_id)


def update_integration_credential(
    session: Session,
    credential: models.IntegrationCredential,
    credential_in: schemas.IntegrationCredentialUpdate,
) -> models.IntegrationCredential:
    for field, value in credential_in.model_dump(exclude_unset=True).items():
        setattr(credential, field, value)
    session.add(credential)
    session.flush()
    return credential


# Flight booking helpers


def list_flight_bookings(
    session: Session,
    *,
    agency_id: int | None = None,
    client_id: int | None = None,
    itinerary_id: int | None = None,
    status: str | None = None,
) -> Sequence[models.FlightBooking]:
    statement = (
        select(models.FlightBooking)
        .options(
            selectinload(models.FlightBooking.segments),
            selectinload(models.FlightBooking.client),
            selectinload(models.FlightBooking.agency),
            selectinload(models.FlightBooking.itinerary),
        )
        .order_by(models.FlightBooking.created_at.desc())
    )
    if agency_id is not None:
        statement = statement.where(models.FlightBooking.agency_id == agency_id)
    if client_id is not None:
        statement = statement.where(models.FlightBooking.client_id == client_id)
    if itinerary_id is not None:
        statement = statement.where(models.FlightBooking.itinerary_id == itinerary_id)
    if status is not None:
        statement = statement.where(models.FlightBooking.status == status)
    return session.scalars(statement).unique().all()


def get_flight_booking(
    session: Session, booking_id: int
) -> models.FlightBooking | None:
    statement = (
        select(models.FlightBooking)
        .options(
            selectinload(models.FlightBooking.segments),
            selectinload(models.FlightBooking.client),
            selectinload(models.FlightBooking.agency),
            selectinload(models.FlightBooking.itinerary),
        )
        .where(models.FlightBooking.id == booking_id)
    )
    return session.scalars(statement).unique().first()


def create_flight_booking(
    session: Session, payload: schemas.FlightBookingCreate
) -> models.FlightBooking:
    data = payload.model_dump(exclude={"segments"})
    segments = payload.segments
    booking = models.FlightBooking(**data)
    booking.pnr = _generate_unique_pnr(session)
    session.add(booking)
    session.flush()

    for segment in segments:
        segment_data = segment.model_dump()
        session.add(models.FlightSegment(booking_id=booking.id, **segment_data))

    session.flush()

    agency = session.get(models.TravelAgency, booking.agency_id)
    client = session.get(models.Client, booking.client_id) if booking.client_id else None
    metadata: Dict[str, Any] = {
        "booking_id": booking.id,
        "pnr": booking.pnr,
        "provider": booking.provider,
    }
    if agency:
        _notify_contact(
            session,
            "flight.booking.created",
            subject="New flight booking created",
            message=f"A new flight booking ({booking.pnr}) has been created.",
            email=agency.contact_email,
            phone=agency.contact_phone,
            metadata=metadata,
        )
    if client:
        _notify_contact(
            session,
            "flight.booking.created",
            subject="Your flight itinerary is being prepared",
            message=f"We are arranging flights under reference {booking.pnr}.",
            email=client.email,
            phone=client.phone,
            metadata=metadata,
        )
    return booking


def update_flight_booking(
    session: Session, booking: models.FlightBooking, payload: schemas.FlightBookingUpdate
) -> models.FlightBooking:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(booking, field, value)
    session.add(booking)
    session.flush()
    return booking


def issue_flight_tickets(
    session: Session,
    booking: models.FlightBooking,
    payload: schemas.FlightTicketIssueRequest,
) -> models.FlightBooking:
    booking.ticket_numbers = payload.ticket_numbers
    if payload.document_url is not None:
        booking.ticket_document_url = payload.document_url
    booking.ticket_issued_at = datetime.utcnow()
    booking.status = payload.status or "ticketed"
    session.add(booking)
    session.flush()

    agency = session.get(models.TravelAgency, booking.agency_id)
    client = session.get(models.Client, booking.client_id) if booking.client_id else None
    metadata: Dict[str, Any] = {
        "booking_id": booking.id,
        "pnr": booking.pnr,
        "provider": booking.provider,
        "ticket_numbers": payload.ticket_numbers,
    }
    if client:
        _notify_contact(
            session,
            "flight.ticket.issued",
            subject="Your flight tickets are ready",
            message=f"Tickets for booking {booking.pnr} have been issued.",
            email=client.email,
            phone=client.phone,
            metadata=metadata,
        )
    if agency:
        _notify_contact(
            session,
            "flight.ticket.issued",
            subject="Flight tickets issued",
            message=f"Tickets for booking {booking.pnr} have been issued.",
            email=agency.contact_email,
            phone=agency.contact_phone,
            metadata=metadata,
        )
    return booking


# Site settings & notifications summary


def upsert_site_setting(
    session: Session, *, key: str, value: str
) -> models.SiteSetting:
    statement = select(models.SiteSetting).where(models.SiteSetting.key == key)
    setting = session.scalars(statement).first()
    if setting:
        setting.value = value
    else:
        setting = models.SiteSetting(key=key, value=value)
    session.add(setting)
    session.flush()
    return setting


def list_site_settings(session: Session) -> Sequence[models.SiteSetting]:
    statement = select(models.SiteSetting).order_by(models.SiteSetting.key)
    return session.scalars(statement).all()


def get_landing_page_content(session: Session) -> schemas.LandingPageContent:
    settings_map = {setting.key: setting.value for setting in list_site_settings(session)}
    data: dict[str, object] = {}

    for field in LANDING_PAGE_TEXT_FIELDS:
        if field in settings_map and settings_map[field] is not None:
            data[field] = settings_map[field]
        elif field in DEFAULT_LANDING_PAGE:
            data[field] = DEFAULT_LANDING_PAGE[field]

    keywords_raw = settings_map.get("meta_keywords")
    if keywords_raw is not None:
        keywords = [piece.strip() for piece in keywords_raw.split(",") if piece.strip()]
        data["meta_keywords"] = keywords or None
    else:
        default_keywords = DEFAULT_LANDING_PAGE.get("meta_keywords") or []
        data["meta_keywords"] = list(default_keywords) if default_keywords else None

    return schemas.LandingPageContent(**data)


def update_landing_page_content(
    session: Session, payload: schemas.LandingPageContentUpdate
) -> schemas.LandingPageContent:
    data = payload.model_dump(exclude_unset=True)
    for field in LANDING_PAGE_TEXT_FIELDS:
        if field in data:
            value = data[field] if data[field] is not None else ""
            upsert_site_setting(session, key=field, value=str(value))

    if "meta_keywords" in data:
        keywords = data["meta_keywords"] or []
        joined = ",".join(keyword.strip() for keyword in keywords if keyword and keyword.strip())
        upsert_site_setting(session, key="meta_keywords", value=joined)

    session.flush()
    return get_landing_page_content(session)


def list_notifications(session: Session, limit: int = 100) -> Sequence[models.NotificationLog]:
    statement = (
        select(models.NotificationLog)
        .order_by(models.NotificationLog.created_at.desc())
        .limit(limit)
    )
    return session.scalars(statement).all()


def notification_summary(session: Session) -> schemas.NotificationSummary:
    notifications = list_notifications(session, limit=1000)
    by_channel: Dict[str, int] = {}
    for notification in notifications:
        by_channel[notification.channel] = by_channel.get(notification.channel, 0) + 1
    return schemas.NotificationSummary(total_sent=len(notifications), by_channel=by_channel)


def get_analytics_overview(session: Session) -> schemas.AnalyticsOverview:
    total_clients = session.scalar(select(func.count(models.Client.id))) or 0
    total_itineraries = session.scalar(select(func.count(models.Itinerary.id))) or 0
    total_revenue = session.scalar(select(func.sum(models.Payment.amount))) or Decimal("0")
    upcoming_departures = (
        session.scalar(
            select(func.count(models.Itinerary.id)).where(
                models.Itinerary.start_date >= date.today()
            )
        )
        or 0
    )
    average_margin = session.scalar(select(func.avg(models.Itinerary.calculated_margin)))
    revenue_rows = session.execute(
        select(
            func.strftime("%Y-%m", models.Payment.paid_on),
            func.sum(models.Payment.amount),
        )
        .group_by(func.strftime("%Y-%m", models.Payment.paid_on))
        .order_by(func.strftime("%Y-%m", models.Payment.paid_on))
    ).all()
    trend = [
        schemas.AnalyticsDataPoint(label=row[0], value=row[1] or Decimal("0"))
        for row in revenue_rows
    ]
    return schemas.AnalyticsOverview(
        total_clients=int(total_clients),
        total_itineraries=int(total_itineraries),
        total_revenue=Decimal(total_revenue or 0),
        upcoming_departures=int(upcoming_departures),
        average_margin=Decimal(average_margin) if average_margin is not None else None,
        revenue_trend=trend,
    )
