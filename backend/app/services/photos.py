"""Фотографии устройства: валидация, сохранение файлов, удаление.

Файлы пишутся на диск до коммита; при ошибке уже записанные удаляются —
в БД не остаётся строк без файлов, а на диске — файлов без строк.
"""

from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import AppError
from app.models import ConditionReport, Device, DevicePhoto, User
from app.services.access import ensure_can_act_on_hold
from app.services.device_state import record_event

MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_PHOTOS_PER_DEVICE = 5
THUMB_WIDTH = 400
_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def photo_url(path: str) -> str:
    """Публичный URL сохранённого файла (раздаётся без сессии)."""
    return f"/media/{path}"


def list_photos(db: Session, device_id: int) -> list[DevicePhoto]:
    """Фото устройства: сначала новые, при равенстве времени — по id."""
    return list(
        db.scalars(
            select(DevicePhoto)
            .where(DevicePhoto.device_id == device_id)
            .order_by(DevicePhoto.created_at.desc(), DevicePhoto.id.desc())
        ).all()
    )


def photos_by_report(db: Session, device_id: int) -> dict[int | None, list[DevicePhoto]]:
    """Фото устройства, сгруппированные по отчёту — одним запросом."""
    grouped: dict[int | None, list[DevicePhoto]] = {}
    for photo in list_photos(db, device_id):
        grouped.setdefault(photo.report_id, []).append(photo)
    return grouped


def _decode(data: bytes) -> tuple[Image.Image, str]:
    """Проверяет размер и формат по содержимому, возвращает изображение."""
    if len(data) > MAX_PHOTO_BYTES:
        raise AppError(
            "PHOTO_TOO_LARGE",
            f"Фото больше {MAX_PHOTO_BYTES // (1024 * 1024)} МБ",
            422,
        )
    try:
        with Image.open(BytesIO(data)) as image:
            image.load()
            if image.format not in _EXTENSIONS:
                raise AppError(
                    "UNSUPPORTED_FORMAT",
                    "Поддерживаются только JPEG, PNG и WebP",
                    422,
                )
            return image.copy(), image.format
    except UnidentifiedImageError as exc:
        raise AppError(
            "UNSUPPORTED_FORMAT",
            "Поддерживаются только JPEG, PNG и WebP",
            422,
        ) from exc
    except OSError as exc:
        raise AppError("UNSUPPORTED_FORMAT", "Файл повреждён", 422) from exc


def _device_dir(device_id: int) -> Path:
    return settings.media_dir / "devices" / str(device_id)


def _save(original: Image.Image, device_id: int, fmt: str) -> tuple[str, str, Path, Path]:
    """Пишет оригинал без EXIF и превью; возвращает пути для БД и диска."""
    directory = _device_dir(device_id)
    directory.mkdir(parents=True, exist_ok=True)
    stem = uuid4().hex
    extension = _EXTENSIONS[fmt]

    file_rel = f"devices/{device_id}/{stem}{extension}"
    thumb_rel = f"devices/{device_id}/{stem}_thumb{extension}"
    file_path = settings.media_dir / file_rel
    thumb_path = settings.media_dir / thumb_rel

    oriented = ImageOps.exif_transpose(original)
    # Вычищаем EXIF: пересохранение без блока exif (F2).
    oriented.info.pop("exif", None)
    if extension == ".jpg":
        oriented = oriented.convert("RGB")
    oriented.save(file_path)  # пересохранение вычищает EXIF (F2)

    thumb = oriented.copy()
    thumb.thumbnail((THUMB_WIDTH, THUMB_WIDTH))
    thumb.save(thumb_path)
    return file_rel, thumb_rel, file_path, thumb_path


def _unlink(*paths: Path) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


def _validate_report(db: Session, device: Device, report_id: int | None) -> None:
    if report_id is None:
        return
    report = db.get(ConditionReport, report_id)
    if report is None or report.device_id != device.id:
        raise AppError(
            "REPORT_DEVICE_MISMATCH",
            "Отчёт не принадлежит этому устройству",
            422,
        )


def upload_photos(
    db: Session,
    device: Device,
    actor: User,
    payloads: list[bytes],
    report_id: int | None = None,
) -> list[DevicePhoto]:
    """Сохраняет пачку фото: валидация всех файлов до записи на диск."""
    ensure_can_act_on_hold(db, device, actor)
    if device.archived_at is not None:
        raise AppError(
            "DEVICE_ARCHIVED",
            "Устройство в архиве: сначала восстановите его",
            409,
        )
    _validate_report(db, device, report_id)

    existing = db.scalar(
        select(func.count()).select_from(DevicePhoto).where(
            DevicePhoto.device_id == device.id
        )
    )
    if (existing or 0) + len(payloads) > MAX_PHOTOS_PER_DEVICE:
        raise AppError(
            "PHOTO_LIMIT",
            f"Не более {MAX_PHOTOS_PER_DEVICE} фото на устройство",
            422,
        )

    # Валидация всей пачки до записи файлов: невалидный файл = ничего не сохранено.
    images = [_decode(data) for data in payloads]

    written: list[Path] = []
    photos: list[DevicePhoto] = []
    try:
        for image, fmt in images:
            file_rel, thumb_rel, file_path, thumb_path = _save(image, device.id, fmt)
            written.extend((file_path, thumb_path))
            photo = DevicePhoto(
                device_id=device.id,
                report_id=report_id,
                file_path=file_rel,
                thumb_path=thumb_rel,
                uploaded_by=actor.id,
            )
            db.add(photo)
            db.flush()
            record_event(
                db,
                device_id=device.id,
                actor_id=actor.id,
                event_type="photo_added",
                payload={"photo_id": photo.id, "report_id": report_id},
            )
            photos.append(photo)
        db.commit()
    except Exception:
        db.rollback()
        _unlink(*written)
        raise

    for photo in photos:
        db.refresh(photo)
    return photos


def delete_photo(db: Session, photo: DevicePhoto, actor: User) -> None:
    """Удаляет фото: автор, владелец устройства или admin; файлы — с диска."""
    device = db.get(Device, photo.device_id)
    if device is None:
        raise AppError("NOT_FOUND", "Устройство не найдено", 404)
    if device.archived_at is not None:
        raise AppError(
            "DEVICE_ARCHIVED",
            "Устройство в архиве: сначала восстановите его",
            409,
        )
    if actor.role != "admin" and actor.id not in {photo.uploaded_by, device.owner_id}:
        raise AppError(
            "FORBIDDEN",
            "Удалять фото может автор, владелец устройства или администратор",
            403,
        )

    file_path = settings.media_dir / photo.file_path
    thumb_path = settings.media_dir / photo.thumb_path
    photo_id = photo.id
    try:
        db.delete(photo)
        record_event(
            db,
            device_id=device.id,
            actor_id=actor.id,
            event_type="photo_removed",
            payload={"photo_id": photo_id},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    _unlink(file_path, thumb_path)
