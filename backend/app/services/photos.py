"""Фотографии устройства: валидация, сохранение файлов, удаление.

Файлы пишутся на диск до коммита; при ошибке уже записанные удаляются —
в БД не остаётся строк без файлов, а на диске — файлов без строк.
"""

import warnings
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.config import settings
from app.errors import AppError
from app.models import ConditionReport, Device, DevicePhoto, User
from app.services.access import ensure_can_act_on_hold
from app.services.device_state import record_event

MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_PHOTOS_PER_DEVICE = 5
THUMB_WIDTH = 400
# 20 Мп ≈ 60 МБ RGB на изображение — с запасом для реальных фото, но без риска OOM.
# Явно ниже стандартных 89 Мп Pillow, где включено только предупреждение.
MAX_IMAGE_PIXELS = 20_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

_SUPPORTED_FORMATS = ("JPEG", "PNG", "WEBP")
_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
_MAX_TOTAL_BYTES = MAX_PHOTOS_PER_DEVICE * MAX_PHOTO_BYTES
_READ_CHUNK = 1024 * 1024


def _too_large_error() -> AppError:
    """Единая ошибка превышения объёма одного фото или всей пачки."""
    return AppError(
        "PHOTO_TOO_LARGE",
        f"Фото больше {MAX_PHOTO_BYTES // (1024 * 1024)} МБ",
        422,
    )


def get_photo(db: Session, photo_id: int) -> DevicePhoto:
    """Фото по id с единым ответом 404 (по образцу services/lookup.py)."""
    photo = db.get(DevicePhoto, photo_id)
    if photo is None:
        raise AppError("NOT_FOUND", "Фото не найдено", 404)
    return photo


def _check_photo_count(db: Session, device: Device, incoming: int) -> None:
    existing = db.scalar(
        select(func.count()).select_from(DevicePhoto).where(DevicePhoto.device_id == device.id)
    )
    if (existing or 0) + incoming > MAX_PHOTOS_PER_DEVICE:
        raise AppError(
            "PHOTO_LIMIT",
            f"Не более {MAX_PHOTOS_PER_DEVICE} фото на устройство",
            422,
        )


def check_upload_preconditions(
    db: Session,
    device: Device,
    actor: User,
    *,
    file_count: int,
    report_id: int | None = None,
) -> None:
    """Права, состояние устройства, отчёт и лимит фото — до чтения байтов файлов."""
    ensure_can_act_on_hold(db, device, actor)
    if device.archived_at is not None:
        raise AppError(
            "DEVICE_ARCHIVED",
            "Устройство в архиве: сначала восстановите его",
            409,
        )
    _validate_report(db, device, report_id)
    _check_photo_count(db, device, file_count)


def _validate_batch(files: Sequence[UploadFile]) -> None:
    """Лимиты пачки по метаданным: число файлов, каждый файл и суммарный объём."""
    if len(files) > MAX_PHOTOS_PER_DEVICE:
        raise AppError(
            "PHOTO_LIMIT",
            f"Не более {MAX_PHOTOS_PER_DEVICE} фото на устройство",
            422,
        )
    total = 0
    for file in files:
        # size вычисляется сервером из contents запроса; None/отсутствует — читаем порциями.
        size = getattr(file, "size", None)
        if size is not None:
            if size > MAX_PHOTO_BYTES:
                raise _too_large_error()
            total += size
    if total > _MAX_TOTAL_BYTES:
        raise AppError("PHOTO_TOO_LARGE", "Суммарный объём фото превышает лимит", 422)


def _read_bounded(file: UploadFile) -> bytes:
    """Читает не больше MAX_PHOTO_BYTES + 1 байт: лишний байт означает превышение."""
    chunks: list[bytes] = []
    total = 0
    limit = MAX_PHOTO_BYTES + 1
    while total < limit:
        chunk = file.file.read(_READ_CHUNK)
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    if total > MAX_PHOTO_BYTES:
        raise _too_large_error()
    return b"".join(chunks)


def read_uploads(files: Sequence[UploadFile]) -> list[bytes]:
    """Проверяет объём пачки до чтения и читает файлы с ранним отказом по лимиту."""
    _validate_batch(files)
    return [_read_bounded(file) for file in files]


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
    """Проверяет размер, формат и число пикселей по содержимому, возвращает изображение."""
    if len(data) > MAX_PHOTO_BYTES:
        raise _too_large_error()
    try:
        # Предупреждение Pillow при 1x лимита превращается в исключение, чтобы
        # «бомба» в диапазоне 20–40 Мп тоже отклонялась, а не только >40 Мп.
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data), formats=_SUPPORTED_FORMATS) as image:
                width, height = image.size
                if width * height > MAX_IMAGE_PIXELS:
                    raise AppError(
                        "UNSUPPORTED_FORMAT",
                        "Изображение слишком большое по числу пикселей",
                        422,
                    )
                image.load()
                if image.format not in _EXTENSIONS:
                    raise AppError(
                        "UNSUPPORTED_FORMAT",
                        "Поддерживаются только JPEG, PNG и WebP",
                        422,
                    )
                return image.copy(), image.format
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise AppError(
            "UNSUPPORTED_FORMAT",
            "Изображение слишком большое по числу пикселей",
            422,
        ) from exc
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
    """Сохраняет пачку фото: валидация всех файлов до записи на диск.

    Повторяет проверки доступа и лимитов (defense in depth): роут вызывает тот же
    префлайт до чтения байтов, но сервис не доверяет вызывающему.
    """
    check_upload_preconditions(db, device, actor, file_count=len(payloads), report_id=report_id)

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
