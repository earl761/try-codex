"""Shared FastAPI dependencies."""
from __future__ import annotations

import json
from datetime import date
from typing import Generator, List, Optional

from fastapi import HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import schemas
from ..database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Provide a scoped database session to request handlers."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:  # pragma: no cover - safety rollback
        db.rollback()
        raise
    finally:
        db.close()


def get_flight_search_request(
    trip_type: str = Query(
        "one_way", description="Journey type such as one_way, round_trip, or multi_city"
    ),
    origin: Optional[str] = Query(
        None, min_length=3, max_length=3, description="IATA origin code"
    ),
    destination: Optional[str] = Query(
        None, min_length=3, max_length=3, description="IATA destination code"
    ),
    departure_date: Optional[date] = Query(None),
    return_date: Optional[date] = Query(None),
    segments: Optional[str] = Query(
        None,
        description="JSON array of segment objects for multi-city journeys",
    ),
    passengers: int = Query(1, ge=1, le=9),
    travel_class: Optional[str] = Query(
        None, description="Preferred cabin such as ECONOMY, PREMIUM_ECONOMY, BUSINESS"
    ),
) -> schemas.FlightSearchRequest:
    """Parse raw query parameters into a validated flight search request."""

    segment_models: Optional[List[schemas.FlightSearchSegment]] = None
    if segments:
        try:
            raw_segments = json.loads(segments)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="segments must be a JSON array of segment objects",
            ) from exc
        if not isinstance(raw_segments, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="segments must decode to a JSON array",
            )
        segment_models = []
        for index, item in enumerate(raw_segments):
            if not isinstance(item, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"segment at position {index} must be a JSON object",
                )
            segment_models.append(
                schemas.FlightSearchSegment.model_validate(item)
            )

    return schemas.FlightSearchRequest(
        trip_type=trip_type,
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        segments=segment_models,
        passengers=passengers,
        travel_class=travel_class,
    )
