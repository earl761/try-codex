"""Media asset management endpoints."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Response, UploadFile, status
from sqlalchemy.orm import Session

from ... import crud, schemas, utils
from ..deps import get_db

router = APIRouter(prefix="/media", tags=["media"])


@router.post(
    "/assets",
    response_model=schemas.MediaAsset,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and optimize a media asset",
)
async def upload_media_asset(
    file: UploadFile = File(...),
    agency_id: Optional[int] = Form(None),
    uploaded_by_id: Optional[int] = Form(None),
    alt_text: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> schemas.MediaAsset:
    raw_bytes = await file.read()
    try:
        optimization = utils.optimize_image_upload(raw_bytes, file.filename or "upload.jpg")
    except ValueError as exc:  # pragma: no cover - runtime validation
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    asset = crud.create_media_asset(
        db,
        filename=file.filename or optimization["optimized_path"].split("/")[-1],
        content_type=file.content_type or "image/jpeg",
        original_path=optimization["original_path"],
        optimized_path=optimization["optimized_path"],
        width=int(optimization["width"]),
        height=int(optimization["height"]),
        file_size=int(optimization["file_size"]),
        agency_id=agency_id,
        uploaded_by_id=uploaded_by_id,
        alt_text=alt_text,
        tags=tags.split(",") if tags else None,
    )
    return schemas.MediaAsset.model_validate(asset)


@router.get("/assets", response_model=list[schemas.MediaAsset])
def list_media_assets(db: Session = Depends(get_db)) -> list[schemas.MediaAsset]:
    assets = crud.list_media_assets(db)
    return [schemas.MediaAsset.model_validate(asset) for asset in assets]


@router.get("/assets/{asset_id}", response_model=schemas.MediaAsset)
def get_media_asset(
    asset_id: Annotated[int, Path(gt=0)], db: Session = Depends(get_db)
) -> schemas.MediaAsset:
    asset = crud.get_media_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
    return schemas.MediaAsset.model_validate(asset)


@router.patch("/assets/{asset_id}", response_model=schemas.MediaAsset)
def update_media_asset(
    asset_id: Annotated[int, Path(gt=0)],
    payload: schemas.MediaAssetUpdate,
    db: Session = Depends(get_db),
) -> schemas.MediaAsset:
    asset = crud.get_media_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
    asset = crud.update_media_asset(db, asset, payload)
    return schemas.MediaAsset.model_validate(asset)


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media_asset(
    asset_id: Annotated[int, Path(gt=0)], db: Session = Depends(get_db)
) -> Response:
    asset = crud.get_media_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
    crud.delete_media_asset(db, asset)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
