"""Эндпоинты фотографий устройства: загрузка, список, удаление."""

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.serializers import user_brief, users_by_id
from app.db import get_db
from app.errors import AppError
from app.models import DevicePhoto, User
from app.schemas.photos import PhotoRead
from app.services import devices as devices_service
from app.services import photos as photos_service

router = APIRouter(tags=["photos"])


def _photo_read(photo: DevicePhoto, users: dict[int, User]) -> PhotoRead:
    return PhotoRead(
        id=photo.id,
        device_id=photo.device_id,
        report_id=photo.report_id,
        url=photos_service.photo_url(photo.file_path),
        thumb_url=photos_service.photo_url(photo.thumb_path),
        uploaded_by=user_brief(users[photo.uploaded_by]),
        created_at=photo.created_at,
    )


def _photo_list(db: Session, photos: list[DevicePhoto]) -> list[PhotoRead]:
    users = users_by_id(db, [photo.uploaded_by for photo in photos])
    return [_photo_read(photo, users) for photo in photos]


@router.post(
    "/devices/{device_id}/photos",
    response_model=list[PhotoRead],
    status_code=status.HTTP_201_CREATED,
)
def upload_photos(
    device_id: int,
    files: list[UploadFile] = File(...),
    report_id: int | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PhotoRead]:
    device = devices_service.get_device(db, device_id)
    payloads = [file.file.read() for file in files]
    photos = photos_service.upload_photos(db, device, user, payloads, report_id)
    return _photo_list(db, photos)


@router.get("/devices/{device_id}/photos", response_model=list[PhotoRead])
def read_photos(
    device_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PhotoRead]:
    devices_service.get_device(db, device_id)
    return _photo_list(db, photos_service.list_photos(db, device_id))


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    photo = db.scalar(select(DevicePhoto).where(DevicePhoto.id == photo_id))
    if photo is None:
        raise AppError("NOT_FOUND", "Фото не найдено", 404)
    photos_service.delete_photo(db, photo, user)
