"""Client management endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from ... import crud, models, schemas
from ..deps import get_db

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("", response_model=schemas.Client, status_code=status.HTTP_201_CREATED)
def create_client(client_in: schemas.ClientCreate, db: Session = Depends(get_db)) -> models.Client:
    return crud.create_client(db, client_in)


@router.get("", response_model=List[schemas.Client])
def list_clients(
    db: Session = Depends(get_db),
    search: str | None = Query(None, description="Filter clients by name or email substring"),
) -> List[models.Client]:
    clients = crud.list_clients(db)
    if search:
        lowered = search.lower()
        clients = [
            client
            for client in clients
            if lowered in (client.name or "").lower()
            or lowered in (client.email or "").lower()
        ]
    return list(clients)


@router.get("/{client_id}", response_model=schemas.Client)
def get_client(client_id: int = Path(..., gt=0), db: Session = Depends(get_db)) -> models.Client:
    client = crud.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=schemas.Client)
def update_client(
    client_id: int,
    client_in: schemas.ClientUpdate,
    db: Session = Depends(get_db),
) -> models.Client:
    client = crud.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return crud.update_client(db, client, client_in)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, db: Session = Depends(get_db)) -> Response:
    client = crud.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    crud.delete_client(db, client)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
