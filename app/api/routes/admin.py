"""Administrative endpoints for managing agencies, integrations, and notifications."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from ... import crud, schemas
from ..deps import get_db, require_super_admin


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/agencies", response_model=list[schemas.TravelAgency])
def list_agencies(db: Session = Depends(get_db)) -> list[schemas.TravelAgency]:
    agencies = crud.list_travel_agencies(db)
    return [schemas.TravelAgency.model_validate(agency) for agency in agencies]


@router.post("/agencies", response_model=schemas.TravelAgency, status_code=status.HTTP_201_CREATED)
def create_agency(
    payload: schemas.TravelAgencyCreate, db: Session = Depends(get_db)
) -> schemas.TravelAgency:
    agency = crud.create_travel_agency(db, payload)
    return schemas.TravelAgency.model_validate(agency)


@router.put("/agencies/{agency_id}", response_model=schemas.TravelAgency)
def update_agency(
    agency_id: Annotated[int, Path(gt=0)],
    payload: schemas.TravelAgencyUpdate,
    db: Session = Depends(get_db),
) -> schemas.TravelAgency:
    agency = crud.get_travel_agency(db, agency_id)
    if not agency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    agency = crud.update_travel_agency(db, agency, payload)
    return schemas.TravelAgency.model_validate(agency)


@router.get("/packages", response_model=list[schemas.SubscriptionPackage])
def list_packages(db: Session = Depends(get_db)) -> list[schemas.SubscriptionPackage]:
    packages = crud.list_subscription_packages(db)
    return [schemas.SubscriptionPackage.model_validate(pkg) for pkg in packages]


@router.post(
    "/packages",
    response_model=schemas.SubscriptionPackage,
    status_code=status.HTTP_201_CREATED,
)
def create_package(
    payload: schemas.SubscriptionPackageCreate, db: Session = Depends(get_db)
) -> schemas.SubscriptionPackage:
    package = crud.create_subscription_package(db, payload)
    return schemas.SubscriptionPackage.model_validate(package)


@router.put("/packages/{package_id}", response_model=schemas.SubscriptionPackage)
def update_package(
    package_id: Annotated[int, Path(gt=0)],
    payload: schemas.SubscriptionPackageUpdate,
    db: Session = Depends(get_db),
) -> schemas.SubscriptionPackage:
    package = crud.get_subscription_package(db, package_id)
    if not package:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    package = crud.update_subscription_package(db, package, payload)
    return schemas.SubscriptionPackage.model_validate(package)


@router.get(
    "/subscriptions",
    response_model=list[schemas.AgencySubscription],
)
def list_subscriptions(
    agency_id: Annotated[int | None, Query(gt=0)] = None,
    db: Session = Depends(get_db),
) -> list[schemas.AgencySubscription]:
    subscriptions = crud.list_agency_subscriptions(db, agency_id=agency_id)
    return [schemas.AgencySubscription.model_validate(sub) for sub in subscriptions]


@router.post(
    "/subscriptions",
    response_model=schemas.AgencySubscription,
    status_code=status.HTTP_201_CREATED,
)
def create_subscription(
    payload: schemas.AgencySubscriptionCreate, db: Session = Depends(get_db)
) -> schemas.AgencySubscription:
    if not crud.get_travel_agency(db, payload.agency_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    if not crud.get_subscription_package(db, payload.package_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    subscription = crud.create_agency_subscription(db, payload)
    subscription = crud.get_agency_subscription(db, subscription.id) or subscription
    return schemas.AgencySubscription.model_validate(subscription)


@router.put("/subscriptions/{subscription_id}", response_model=schemas.AgencySubscription)
def update_subscription(
    subscription_id: Annotated[int, Path(gt=0)],
    payload: schemas.AgencySubscriptionUpdate,
    db: Session = Depends(get_db),
) -> schemas.AgencySubscription:
    subscription = crud.get_agency_subscription(db, subscription_id)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    if payload.package_id is not None and not crud.get_subscription_package(db, payload.package_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    subscription = crud.update_agency_subscription(db, subscription, payload)
    subscription = crud.get_agency_subscription(db, subscription.id) or subscription
    return schemas.AgencySubscription.model_validate(subscription)


@router.post(
    "/api-keys",
    response_model=schemas.IntegrationCredential,
    status_code=status.HTTP_201_CREATED,
)
def create_integration_key(
    payload: schemas.IntegrationCredentialCreate, db: Session = Depends(get_db)
) -> schemas.IntegrationCredential:
    if not crud.get_travel_agency(db, payload.agency_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    credential = crud.create_integration_credential(db, payload)
    return schemas.IntegrationCredential.model_validate(credential)


@router.put("/api-keys/{credential_id}", response_model=schemas.IntegrationCredential)
def update_integration_key(
    credential_id: int,
    payload: schemas.IntegrationCredentialUpdate,
    db: Session = Depends(get_db),
) -> schemas.IntegrationCredential:
    credential = crud.get_integration_credential(db, credential_id)
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    credential = crud.update_integration_credential(db, credential, payload)
    return schemas.IntegrationCredential.model_validate(credential)


@router.get("/api-keys", response_model=list[schemas.IntegrationCredential])
def list_integration_keys(db: Session = Depends(get_db)) -> list[schemas.IntegrationCredential]:
    credentials = crud.list_integration_credentials(db)
    return [schemas.IntegrationCredential.model_validate(cred) for cred in credentials]


@router.get("/payment-gateways", response_model=list[schemas.PaymentGateway])
def list_payment_gateways(db: Session = Depends(get_db)) -> list[schemas.PaymentGateway]:
    gateways = crud.list_payment_gateways(db)
    return [schemas.PaymentGateway.model_validate(gateway) for gateway in gateways]


@router.post(
    "/payment-gateways",
    response_model=schemas.PaymentGateway,
    status_code=status.HTTP_201_CREATED,
)
def create_payment_gateway(
    payload: schemas.PaymentGatewayCreate, db: Session = Depends(get_db)
) -> schemas.PaymentGateway:
    if payload.agency_id and not crud.get_travel_agency(db, payload.agency_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    gateway = crud.create_payment_gateway(db, payload)
    return schemas.PaymentGateway.model_validate(gateway)


@router.put(
    "/payment-gateways/{gateway_id}",
    response_model=schemas.PaymentGateway,
)
def update_payment_gateway(
    gateway_id: Annotated[int, Path(gt=0)],
    payload: schemas.PaymentGatewayUpdate,
    db: Session = Depends(get_db),
) -> schemas.PaymentGateway:
    gateway = crud.get_payment_gateway(db, gateway_id)
    if not gateway:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment gateway not found")
    if payload.agency_id and not crud.get_travel_agency(db, payload.agency_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    gateway = crud.update_payment_gateway(db, gateway, payload)
    return schemas.PaymentGateway.model_validate(gateway)


@router.delete("/payment-gateways/{gateway_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment_gateway(
    gateway_id: Annotated[int, Path(gt=0)], db: Session = Depends(get_db)
) -> Response:
    gateway = crud.get_payment_gateway(db, gateway_id)
    if not gateway:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment gateway not found")
    crud.delete_payment_gateway(db, gateway)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/notifications", response_model=list[schemas.NotificationLog])
def list_notifications(db: Session = Depends(get_db)) -> list[schemas.NotificationLog]:
    notifications = crud.list_notifications(db)
    return [schemas.NotificationLog.model_validate(notification) for notification in notifications]


@router.get("/notifications/summary", response_model=schemas.NotificationSummary)
def notifications_summary(db: Session = Depends(get_db)) -> schemas.NotificationSummary:
    return crud.notification_summary(db)


@router.get("/settings", response_model=list[schemas.SiteSetting])
def list_settings(db: Session = Depends(get_db)) -> list[schemas.SiteSetting]:
    settings = crud.list_site_settings(db)
    return [schemas.SiteSetting.model_validate(setting) for setting in settings]


@router.put("/settings/{key}", response_model=schemas.SiteSetting)
def update_setting(key: str, payload: schemas.SiteSettingUpdate, db: Session = Depends(get_db)) -> schemas.SiteSetting:
    setting = crud.upsert_site_setting(db, key=key, value=payload.value)
    return schemas.SiteSetting.model_validate(setting)


@router.get("/landing-page", response_model=schemas.LandingPageContent)
def get_landing_page(
    db: Session = Depends(get_db), _=Depends(require_super_admin)
) -> schemas.LandingPageContent:
    return crud.get_landing_page_content(db)


@router.put("/landing-page", response_model=schemas.LandingPageContent)
def update_landing_page(
    payload: schemas.LandingPageContentUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_super_admin),
) -> schemas.LandingPageContent:
    return crud.update_landing_page_content(db, payload)


@router.get("/media", response_model=list[schemas.MediaAsset])
def list_all_media(db: Session = Depends(get_db)) -> list[schemas.MediaAsset]:
    assets = crud.list_media_assets(db)
    return [schemas.MediaAsset.model_validate(asset) for asset in assets]


@router.patch("/media/{asset_id}", response_model=schemas.MediaAsset)
def update_media(
    asset_id: Annotated[int, Path(gt=0)],
    payload: schemas.MediaAssetUpdate,
    db: Session = Depends(get_db),
) -> schemas.MediaAsset:
    asset = crud.get_media_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
    asset = crud.update_media_asset(db, asset, payload)
    return schemas.MediaAsset.model_validate(asset)


@router.delete("/media/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(asset_id: Annotated[int, Path(gt=0)], db: Session = Depends(get_db)) -> Response:
    asset = crud.get_media_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
    crud.delete_media_asset(db, asset)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
