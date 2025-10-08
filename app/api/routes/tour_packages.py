"""Tour package inventory endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ... import crud, models, schemas
from ..deps import get_db

router = APIRouter(prefix="/packages", tags=["inventory"])


@router.post("", response_model=schemas.TourPackage, status_code=status.HTTP_201_CREATED)
def create_package(
    package_in: schemas.TourPackageCreate, db: Session = Depends(get_db)
) -> models.TourPackage:
    return crud.create_tour_package(db, package_in)


@router.get("", response_model=List[schemas.TourPackage])
def list_packages(db: Session = Depends(get_db)) -> List[models.TourPackage]:
    return list(crud.list_tour_packages(db))


@router.put("/{package_id}", response_model=schemas.TourPackage)
def update_package(
    package_id: int,
    package_in: schemas.TourPackageUpdate,
    db: Session = Depends(get_db),
) -> models.TourPackage:
    package = crud.get_tour_package(db, package_id)
    if not package:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    return crud.update_tour_package(db, package, package_in)


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(package_id: int, db: Session = Depends(get_db)) -> Response:
    package = crud.get_tour_package(db, package_id)
    if not package:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    crud.delete_tour_package(db, package)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
