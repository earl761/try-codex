"""Pydantic schemas powering the Tour Planner API."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationInfo, field_validator


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientBase(BaseModel):
    name: str = Field(..., description="Client full name")
    email: Optional[EmailStr] = Field(None, description="Primary email address")
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    agency_id: Optional[int] = Field(None, description="Owning travel agency identifier")


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    agency_id: Optional[int] = None


class Client(ClientBase, TimestampMixin):
    id: int


class LeadBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    source: Optional[str] = None
    status: str = Field("new", description="Lead status e.g. new, contacted, qualified")
    notes: Optional[str] = None
    client_id: Optional[int] = None
    agency_id: Optional[int] = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    source: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    client_id: Optional[int] = None
    agency_id: Optional[int] = None


class Lead(LeadBase, TimestampMixin):
    id: int


class LeadConversionResult(BaseModel):
    lead: Lead
    client: Client

    model_config = ConfigDict(from_attributes=True)


class TourPackageBase(BaseModel):
    name: str
    destination: str
    duration_days: int
    base_price: Decimal
    description: Optional[str] = None


class TourPackageCreate(TourPackageBase):
    pass


class TourPackageUpdate(BaseModel):
    name: Optional[str] = None
    destination: Optional[str] = None
    duration_days: Optional[int] = None
    base_price: Optional[Decimal] = None
    description: Optional[str] = None


class TourPackage(TourPackageBase, TimestampMixin):
    id: int


class MediaAssetBase(BaseModel):
    agency_id: Optional[int] = Field(
        None, description="Owning travel agency identifier if applicable"
    )
    alt_text: Optional[str] = Field(None, description="Accessible description")
    tags: List[str] = Field(default_factory=list, description="Searchable keywords")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [tag.strip() for tag in value.split(",") if tag.strip()]
        if isinstance(value, list):
            return [str(tag).strip() for tag in value if str(tag).strip()]
        return []


class MediaAsset(MediaAssetBase, TimestampMixin):
    id: int
    filename: str
    content_type: str
    original_path: str
    optimized_path: str
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    uploaded_by_id: Optional[int] = None


class MediaAssetUpdate(BaseModel):
    alt_text: Optional[str] = None
    tags: Optional[List[str]] = None
    agency_id: Optional[int] = None

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: Any) -> Optional[List[str]]:
        if value is None:
            return None
        if isinstance(value, str):
            return [tag.strip() for tag in value.split(",") if tag.strip()]
        if isinstance(value, list):
            return [str(tag).strip() for tag in value if str(tag).strip()]
        return None


class ItineraryItemMediaBase(BaseModel):
    usage: Literal["gallery", "activity", "accommodation", "transport", "highlight"] = Field(
        "gallery", description="Context for displaying the media asset"
    )


class ItineraryItemMediaCreate(ItineraryItemMediaBase):
    asset_id: int


class ItineraryItemMedia(ItineraryItemMediaBase, TimestampMixin):
    id: int
    asset: MediaAsset


class ItineraryItemBase(BaseModel):
    day_number: int
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    category: Literal["activity", "accommodation", "transport", "meal", "other"] = Field(
        "activity", description="Type of experience"
    )
    supplier_reference: Optional[str] = Field(
        None, description="Supplier or booking reference for traceability"
    )
    estimated_cost: Optional[Decimal] = Field(
        None, description="Estimated contribution to the overall budget"
    )
    estimated_currency: str = Field("USD", description="Currency for the estimate")

    @field_validator("day_number")
    @classmethod
    def validate_day_number(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("day_number must be greater than zero")
        return value


class ItineraryItemCreate(ItineraryItemBase):
    media: List[ItineraryItemMediaCreate] = Field(
        default_factory=list, description="Images that illustrate the day"
    )


class ItineraryItem(ItineraryItemBase, TimestampMixin):
    id: int
    media: List[ItineraryItemMedia] = Field(
        default_factory=list,
        validation_alias="media_links",
        serialization_alias="media",
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ItineraryBase(BaseModel):
    client_id: int
    tour_package_id: Optional[int] = None
    title: str
    start_date: date
    end_date: date
    total_price: Optional[Decimal] = None
    status: str = "draft"
    estimate_amount: Optional[Decimal] = Field(
        None, description="Quote value shared with the client"
    )
    estimate_currency: str = Field("USD", description="Currency used for the estimate")
    brand_logo_url: Optional[str] = Field(
        None, description="Logo path or URL for client-facing documents"
    )
    brand_primary_color: Optional[str] = Field(
        None, description="Primary HEX/RGB color applied to itinerary outputs"
    )
    brand_secondary_color: Optional[str] = Field(
        None, description="Secondary HEX/RGB color applied to itinerary outputs"
    )
    brand_footer_note: Optional[str] = Field(
        None, description="Footer notes or disclaimers for printable itineraries"
    )


class ItineraryExtensionBase(BaseModel):
    title: str
    description: Optional[str] = None
    additional_cost: Optional[Decimal] = None
    currency: str = "USD"


class ItineraryExtensionCreate(ItineraryExtensionBase):
    pass


class ItineraryExtension(ItineraryExtensionBase, TimestampMixin):
    id: int


class ItineraryNoteBase(BaseModel):
    category: Literal["packing", "visa", "terms", "destination", "custom"] = Field(
        "custom", description="Type of advisory content"
    )
    title: Optional[str] = Field(None, description="Optional note heading")
    content: str = Field(..., description="Guidance displayed to travelers")


class ItineraryNoteCreate(ItineraryNoteBase):
    pass


class ItineraryNote(ItineraryNoteBase, TimestampMixin):
    id: int


class ItineraryCreate(ItineraryBase):
    items: List[ItineraryItemCreate] = Field(default_factory=list)
    extensions: List[ItineraryExtensionCreate] = Field(
        default_factory=list, description="Optional post-tour or add-on experiences"
    )
    notes: List[ItineraryNoteCreate] = Field(
        default_factory=list,
        description="Reference information such as packing lists, visa requirements, or terms",
    )


class ItineraryUpdate(BaseModel):
    client_id: Optional[int] = None
    tour_package_id: Optional[int] = None
    title: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_price: Optional[Decimal] = None
    status: Optional[str] = None
    items: Optional[List[ItineraryItemCreate]] = None
    estimate_amount: Optional[Decimal] = None
    estimate_currency: Optional[str] = None
    brand_logo_url: Optional[str] = None
    brand_primary_color: Optional[str] = None
    brand_secondary_color: Optional[str] = None
    brand_footer_note: Optional[str] = None
    extensions: Optional[List[ItineraryExtensionCreate]] = None
    notes: Optional[List[ItineraryNoteCreate]] = None


class Itinerary(ItineraryBase, TimestampMixin):
    id: int
    items: List[ItineraryItem]
    extensions: List[ItineraryExtension] = Field(default_factory=list)
    notes: List[ItineraryNote] = Field(default_factory=list)


class InvoiceBase(BaseModel):
    client_id: int
    itinerary_id: Optional[int] = None
    issue_date: date
    due_date: date
    amount: Decimal
    currency: str = "USD"
    status: str = "unpaid"


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    client_id: Optional[int] = None
    itinerary_id: Optional[int] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    status: Optional[str] = None


class Invoice(InvoiceBase, TimestampMixin):
    id: int


class PaymentBase(BaseModel):
    invoice_id: int
    amount: Decimal
    currency: str = "USD"
    paid_on: date
    method: Optional[str] = None
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    invoice_id: Optional[int] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    paid_on: Optional[date] = None
    method: Optional[str] = None
    notes: Optional[str] = None


class Payment(PaymentBase, TimestampMixin):
    id: int


class ExpenseBase(BaseModel):
    description: str
    amount: Decimal
    currency: str = "USD"
    category: Optional[str] = None
    incurred_on: date
    reimbursable: bool = False


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    incurred_on: Optional[date] = None
    reimbursable: Optional[bool] = None


class Expense(ExpenseBase, TimestampMixin):
    id: int


class SupplierRateBase(BaseModel):
    title: str
    category: str = Field("accommodation", description="Inventory type e.g. accommodation")
    description: Optional[str] = None
    rate_type: str = Field("per_night", description="Billing cadence e.g. per_night, per_trip")
    unit: Optional[str] = Field(None, description="Unit such as double room or SUV")
    capacity: Optional[int] = Field(None, ge=1)
    price: Decimal
    currency: str = "USD"
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    refundable: bool = True
    external_code: Optional[str] = Field(None, description="Identifier from external provider")
    availability_notes: Optional[str] = None

    @field_validator("valid_to")
    @classmethod
    def validate_date_range(cls, valid_to: Optional[date], info: ValidationInfo) -> Optional[date]:
        valid_from = info.data.get("valid_from")
        if valid_from and valid_to and valid_to < valid_from:
            raise ValueError("valid_to must be greater than or equal to valid_from")
        return valid_to


class SupplierRateCreate(SupplierRateBase):
    pass


class SupplierRateUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    rate_type: Optional[str] = None
    unit: Optional[str] = None
    capacity: Optional[int] = Field(None, ge=1)
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    refundable: Optional[bool] = None
    external_code: Optional[str] = None
    availability_notes: Optional[str] = None


class SupplierRate(SupplierRateBase, TimestampMixin):
    id: int
    supplier_id: int


class SupplierBase(BaseModel):
    name: str
    supplier_type: str = Field("lodging", description="Supplier segment such as lodging or transport")
    description: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    active: bool = True
    notes: Optional[str] = None
    integration_provider: Optional[str] = Field(
        None, description="External provider powering automated updates"
    )
    integration_reference: Optional[str] = Field(
        None, description="Identifier understood by the integration provider"
    )
    agency_id: Optional[int] = Field(None, description="Travel agency the supplier belongs to")


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    supplier_type: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    active: Optional[bool] = None
    notes: Optional[str] = None
    integration_provider: Optional[str] = None
    integration_reference: Optional[str] = None
    agency_id: Optional[int] = None


class Supplier(SupplierBase, TimestampMixin):
    id: int
    rates: List[SupplierRate] = Field(default_factory=list)


class SupplierIntegration(BaseModel):
    provider: str
    resources: List[str]


class SubscriptionPackageBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal = Field(..., description="Package price for agencies")
    currency: str = Field("USD", description="Currency code for pricing")
    billing_cycle: str = Field(
        "monthly",
        description="Billing cadence such as monthly, quarterly, or yearly",
    )
    features: List[str] = Field(
        default_factory=list,
        description="Key selling points rendered on the landing page",
    )
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)

    @field_validator("features", mode="before")
    @classmethod
    def normalize_features(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [feature.strip() for feature in value.split(",") if feature.strip()]
        if isinstance(value, list):
            return [str(feature).strip() for feature in value if str(feature).strip()]
        return []


class SubscriptionPackageCreate(SubscriptionPackageBase):
    slug: Optional[str] = Field(
        None, description="Optional custom slug for marketing and analytics"
    )


class SubscriptionPackageUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    billing_cycle: Optional[str] = None
    features: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @field_validator("features", mode="before")
    @classmethod
    def normalize_features(cls, value: Any) -> Optional[List[str]]:
        if value is None:
            return None
        if isinstance(value, str):
            return [feature.strip() for feature in value.split(",") if feature.strip()]
        if isinstance(value, list):
            return [str(feature).strip() for feature in value if str(feature).strip()]
        return None


class SubscriptionPackage(SubscriptionPackageBase, TimestampMixin):
    id: int
    slug: str


class AgencySubscriptionBase(BaseModel):
    status: str = Field("active", description="Subscription status e.g. trial, active, cancelled")
    start_date: Optional[date] = Field(None, description="Subscription start date")
    end_date: Optional[date] = Field(None, description="Subscription end date if cancelled")
    auto_renew: bool = True
    notes: Optional[str] = Field(None, description="Internal notes about the subscription")


class AgencySubscriptionCreate(AgencySubscriptionBase):
    agency_id: int
    package_id: int


class AgencySubscriptionUpdate(BaseModel):
    package_id: Optional[int] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    auto_renew: Optional[bool] = None
    notes: Optional[str] = None


class AgencySubscription(AgencySubscriptionBase, TimestampMixin):
    id: int
    agency_id: int
    package_id: int
    package: Optional[SubscriptionPackage] = None

    model_config = ConfigDict(from_attributes=True)


class TravelAgencyBase(BaseModel):
    name: str
    slug: Optional[str] = Field(None, description="SEO friendly slug")
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    active: bool = True
    default_currency: str = "USD"
    logo_url: Optional[str] = Field(None, description="Brand logo path or URL")
    brand_primary_color: Optional[str] = Field(
        None, description="Primary HEX/RGB color for marketing collateral"
    )
    brand_secondary_color: Optional[str] = Field(
        None, description="Secondary HEX/RGB color for marketing collateral"
    )
    invoice_footer: Optional[str] = Field(
        None, description="Default notes appended to invoices"
    )


class TravelAgencyCreate(TravelAgencyBase):
    pass


class TravelAgencyUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    default_currency: Optional[str] = None
    logo_url: Optional[str] = None
    brand_primary_color: Optional[str] = None
    brand_secondary_color: Optional[str] = None
    invoice_footer: Optional[str] = None


class TravelAgency(TravelAgencyBase, TimestampMixin):
    id: int
    subscriptions: List[AgencySubscription] = Field(default_factory=list)


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    whatsapp_number: Optional[str] = None
    agency_id: Optional[int] = None
    is_active: bool = True
    is_admin: bool = False


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    whatsapp_number: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    agency_id: Optional[int] = None


class User(UserBase, TimestampMixin):
    id: int
    two_factor_enabled: bool = False


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    whatsapp_number: Optional[str] = None
    agency_id: Optional[int] = None
    agency_name: Optional[str] = Field(
        None, description="Optional agency name to create alongside the user"
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    otp_code: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User
    two_factor_required: bool = False


class TwoFactorSetupRequest(BaseModel):
    email: EmailStr
    password: str


class TwoFactorSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class TwoFactorVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str


class IntegrationCredentialBase(BaseModel):
    provider: str
    api_key: str
    description: Optional[str] = None
    active: bool = True
    agency_id: int


class IntegrationCredentialCreate(IntegrationCredentialBase):
    pass


class IntegrationCredentialUpdate(BaseModel):
    api_key: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class IntegrationCredential(IntegrationCredentialBase, TimestampMixin):
    id: int


class NotificationLog(BaseModel):
    id: int
    event_type: str
    channel: str
    recipient: str
    subject: Optional[str]
    message: str
    status: str
    context: Optional[str]
    created_at: datetime
    user_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class SiteSettingBase(BaseModel):
    key: str
    value: str


class SiteSettingCreate(SiteSettingBase):
    pass


class SiteSettingUpdate(BaseModel):
    value: str


class SiteSetting(SiteSettingBase, TimestampMixin):
    id: int


class LandingPageContent(BaseModel):
    headline: str
    subheadline: str
    call_to_action: str
    seo_description: str
    hero_image_url: Optional[str] = None
    meta_keywords: Optional[List[str]] = None


class ItineraryInvoiceCreate(BaseModel):
    issue_date: date
    due_date: date
    amount: Optional[Decimal] = Field(
        None, description="Invoice amount; defaults to itinerary estimate when omitted"
    )
    currency: Optional[str] = Field(
        None, description="Currency to use; defaults to itinerary estimate currency"
    )
    notes: Optional[str] = Field(
        None, description="Optional memo or reference for the generated invoice"
    )


class NotificationSummary(BaseModel):
    total_sent: int
    by_channel: Dict[str, int]
