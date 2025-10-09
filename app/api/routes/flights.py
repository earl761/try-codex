"""Flight booking panel endpoints leveraging Amadeus integrations."""
from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ... import crud, schemas, utils
from ..deps import get_db, get_flight_search_request

router = APIRouter(prefix="/flights", tags=["flights"])


@router.get("/providers", response_model=List[schemas.FlightProvider])
def list_providers() -> List[schemas.FlightProvider]:
    providers = utils.list_available_flight_providers()
    return [schemas.FlightProvider.model_validate(provider) for provider in providers]


@router.get("/search", response_model=List[schemas.FlightOffer])
def search_flights(
    params: Annotated[
        schemas.FlightSearchRequest, Depends(get_flight_search_request)
    ],
    provider: Annotated[str, Query(description="Flight provider identifier")] = "amadeus",
) -> List[schemas.FlightOffer]:
    provider_key = provider.lower()
    if provider_key != "amadeus":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only the Amadeus provider is currently supported",
        )
    offers = utils.search_amadeus_flights(
        trip_type=params.trip_type,
        origin=params.origin,
        destination=params.destination,
        departure_date=params.departure_date,
        return_date=params.return_date,
        segments=[segment.model_dump() for segment in params.segments]
        if params.segments
        else None,
        passengers=params.passengers,
        travel_class=params.travel_class,
    )
    return [schemas.FlightOffer.model_validate(offer) for offer in offers]


@router.get("/bookings", response_model=List[schemas.FlightBooking])
def list_bookings(
    agency_id: Annotated[int | None, Query(gt=0)] = None,
    client_id: Annotated[int | None, Query(gt=0)] = None,
    itinerary_id: Annotated[int | None, Query(gt=0)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    db: Session = Depends(get_db),
) -> List[schemas.FlightBooking]:
    bookings = crud.list_flight_bookings(
        db,
        agency_id=agency_id,
        client_id=client_id,
        itinerary_id=itinerary_id,
        status=status_filter,
    )
    return [schemas.FlightBooking.model_validate(booking) for booking in bookings]


@router.post("/bookings", response_model=schemas.FlightBooking, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: schemas.FlightBookingCreate, db: Session = Depends(get_db)
) -> schemas.FlightBooking:
    if not crud.get_travel_agency(db, payload.agency_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found")
    if payload.client_id and not crud.get_client(db, payload.client_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if payload.itinerary_id and not crud.get_itinerary(db, payload.itinerary_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    if not crud.agency_has_module(db, payload.agency_id, "flight_booking"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agency subscription does not include flight booking",
        )
    booking = crud.create_flight_booking(db, payload)
    booking = crud.get_flight_booking(db, booking.id) or booking
    return schemas.FlightBooking.model_validate(booking)


@router.get("/bookings/{booking_id}", response_model=schemas.FlightBooking)
def get_booking(booking_id: int, db: Session = Depends(get_db)) -> schemas.FlightBooking:
    booking = crud.get_flight_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return schemas.FlightBooking.model_validate(booking)


@router.put("/bookings/{booking_id}", response_model=schemas.FlightBooking)
def update_booking(
    booking_id: int, payload: schemas.FlightBookingUpdate, db: Session = Depends(get_db)
) -> schemas.FlightBooking:
    booking = crud.get_flight_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    booking = crud.update_flight_booking(db, booking, payload)
    booking = crud.get_flight_booking(db, booking.id) or booking
    return schemas.FlightBooking.model_validate(booking)


@router.post(
    "/bookings/{booking_id}/ticket",
    response_model=schemas.FlightBooking,
    status_code=status.HTTP_200_OK,
)
def issue_ticket(
    booking_id: int,
    payload: schemas.FlightTicketIssueRequest,
    db: Session = Depends(get_db),
) -> schemas.FlightBooking:
    booking = crud.get_flight_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    booking = crud.issue_flight_tickets(db, booking, payload)
    booking = crud.get_flight_booking(db, booking.id) or booking
    return schemas.FlightBooking.model_validate(booking)


@router.get(
    "/bookings/{booking_id}/ticket",
    response_class=HTMLResponse,
    summary="Render a printable ticket confirmation",
)
def render_ticket(booking_id: int, db: Session = Depends(get_db)) -> HTMLResponse:
    booking = crud.get_flight_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    html = utils.render_flight_ticket(booking)
    return HTMLResponse(content=html)


__all__ = ["router"]
