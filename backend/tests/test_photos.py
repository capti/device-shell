"""Фотографии устройства: загрузка, чтение, удаление, лимиты и права."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from helpers import checkout, create_device, login_as, register_user
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.photos as photos_service
from app.config import settings
from app.errors import AppError
from app.models import DeviceEvent, DevicePhoto

MAX_PHOTO_BYTES = 10 * 1024 * 1024


def image_bytes(fmt: str = "JPEG", *, with_exif: bool = False) -> bytes:
    """Тестовое изображение заданного формата, опционально с EXIF."""
    image = Image.new("RGB", (800, 600), (10, 20, 30))
    kwargs: dict = {}
    if with_exif:
        exif = image.getexif()
        exif[271] = "TestCam"
        kwargs["exif"] = exif
    buffer = BytesIO()
    image.save(buffer, fmt, **kwargs)
    return buffer.getvalue()


def upload(
    client: TestClient, device_id: int, files: list[tuple[str, bytes, str]], **data
) -> dict:
    response = client.post(
        f"/devices/{device_id}/photos",
        files=[("files", (name, content, mime)) for name, content, mime in files],
        data=data,
    )
    return {"status": response.status_code, "body": response.json()}


def test_report_response_contains_photos(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    response = client.post(
        f"/devices/{device['id']}/condition-reports", json={"condition": "ok"}
    )

    assert response.status_code == 201, response.text
    assert response.json()["photos"] == []


def test_upload_saves_original_and_thumb_without_exif(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    result = upload(
        client,
        device["id"],
        [("phone.jpg", image_bytes(with_exif=True), "image/jpeg")],
    )

    assert result["status"] == 201, result["body"]
    photo = result["body"][0]
    assert photo["device_id"] == device["id"]
    assert photo["report_id"] is None
    assert photo["url"].startswith(f"/media/devices/{device['id']}/")
    assert photo["thumb_url"].startswith(f"/media/devices/{device['id']}/")

    original = settings.media_dir / photo["url"].removeprefix("/media/")
    thumb = settings.media_dir / photo["thumb_url"].removeprefix("/media/")
    assert original.exists()
    assert thumb.exists()
    with Image.open(original) as stored:
        assert not stored.getexif()
    with Image.open(thumb) as preview:
        assert preview.width <= 400


def test_upload_keeps_alpha_channel_of_png(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    buffer = BytesIO()
    Image.new("RGBA", (20, 20), (1, 2, 3, 128)).save(buffer, "PNG")

    result = upload(
        client, device["id"], [("alpha.png", buffer.getvalue(), "image/png")]
    )

    assert result["status"] == 201, result["body"]
    stored_path = settings.media_dir / result["body"][0]["url"].removeprefix("/media/")
    with Image.open(stored_path) as stored:
        assert stored.mode == "RGBA"


def test_upload_rejects_file_over_size_limit(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    result = upload(
        client,
        device["id"],
        [("big.jpg", b"x" * (MAX_PHOTO_BYTES + 1), "image/jpeg")],
    )

    assert result["status"] == 422, result["body"]
    assert result["body"]["code"] == "PHOTO_TOO_LARGE"
    assert "10 МБ" in result["body"]["message"]


def test_upload_accepts_file_of_exactly_max_size(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    payload = image_bytes()
    padded = payload + b"\x00" * (MAX_PHOTO_BYTES - len(payload))
    assert len(padded) == MAX_PHOTO_BYTES

    result = upload(client, device["id"], [("limit.jpg", padded, "image/jpeg")])

    assert result["status"] == 201, result["body"]


def test_upload_rejects_unsupported_format(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    result = upload(
        client, device["id"], [("anim.gif", image_bytes("GIF"), "image/gif")]
    )

    assert result["status"] == 422, result["body"]
    assert result["body"]["code"] == "UNSUPPORTED_FORMAT"


def test_upload_rejects_content_that_is_not_an_image(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    result = upload(
        client,
        device["id"],
        [("notes.jpg", b"not an image at all", "image/jpeg")],
    )

    assert result["status"] == 422, result["body"]
    assert result["body"]["code"] == "UNSUPPORTED_FORMAT"


def test_upload_rejects_truncated_image(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    result = upload(
        client, device["id"], [("broken.jpg", image_bytes()[:200], "image/jpeg")]
    )

    assert result["status"] == 422, result["body"]
    assert result["body"]["code"] == "UNSUPPORTED_FORMAT"


def test_upload_rejects_sixth_photo(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    for index in range(5):
        result = upload(
            client,
            device["id"],
            [(f"p{index}.jpg", image_bytes(), "image/jpeg")],
        )
        assert result["status"] == 201, result["body"]

    extra = upload(
        client, device["id"], [("p5.jpg", image_bytes(), "image/jpeg")]
    )

    assert extra["status"] == 422, extra["body"]
    assert extra["body"]["code"] == "PHOTO_LIMIT"
    listing = client.get(f"/devices/{device['id']}/photos")
    assert len(listing.json()) == 5


def test_upload_rejects_report_of_another_device(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    first = create_device(client)
    second = create_device(client, inventory_no="QA-PH-002")
    report_id = client.post(
        f"/devices/{second['id']}/condition-reports", json={"condition": "ok"}
    ).json()["id"]

    result = upload(
        client,
        first["id"],
        [("p.jpg", image_bytes(), "image/jpeg")],
        report_id=str(report_id),
    )

    assert result["status"] == 422, result["body"]
    assert result["body"]["code"] == "REPORT_DEVICE_MISMATCH"


def test_upload_rejects_whole_batch_when_one_file_is_invalid(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    result = upload(
        client,
        device["id"],
        [
            ("good.jpg", image_bytes(), "image/jpeg"),
            ("bad.gif", image_bytes("GIF"), "image/gif"),
        ],
    )

    assert result["status"] == 422, result["body"]
    listing = client.get(f"/devices/{device['id']}/photos")
    assert listing.json() == []


def test_files_are_removed_when_save_fails(
    client: TestClient, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    def boom(*_args, **_kwargs):
        raise RuntimeError("имитация сбоя записи истории")

    monkeypatch.setattr(photos_service, "record_event", boom)

    with pytest.raises(RuntimeError):
        upload(client, device["id"], [("p.jpg", image_bytes(), "image/jpeg")])

    directory = photos_service._device_dir(device["id"])
    assert not directory.exists() or not any(directory.iterdir())


def test_holder_can_upload_photo(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    checkout(client, device["id"], holder)

    client.cookies.clear()
    login_as(client, holder)
    result = upload(
        client, device["id"], [("p.jpg", image_bytes(), "image/jpeg")]
    )

    assert result["status"] == 201, result["body"]
    event = db.scalar(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"],
            DeviceEvent.type == "photo_added",
        )
    )
    assert event is not None
    assert event.payload["photo_id"] == result["body"][0]["id"]


def test_upload_accepts_five_photos_in_one_request(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    result = upload(
        client,
        device["id"],
        [(f"p{index}.jpg", image_bytes(), "image/jpeg") for index in range(5)],
    )

    assert result["status"] == 201, result["body"]
    assert len(result["body"]) == 5


def test_stranger_cannot_upload_photo(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    stranger = register_user(make_user, username="stranger")
    device = create_device(client)

    client.cookies.clear()
    login_as(client, stranger)
    result = upload(
        client, device["id"], [("p.jpg", image_bytes(), "image/jpeg")]
    )

    assert result["status"] == 403, result["body"]
    assert result["body"]["code"] == "FORBIDDEN"


def test_archived_device_rejects_upload(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    assert client.post(f"/devices/{device['id']}/archive").status_code == 200

    result = upload(
        client, device["id"], [("p.jpg", image_bytes(), "image/jpeg")]
    )

    assert result["status"] == 409, result["body"]
    assert result["body"]["code"] == "DEVICE_ARCHIVED"


def _uploaded(client: TestClient, device_id: int) -> dict:
    result = upload(
        client, device_id, [("p.jpg", image_bytes(), "image/jpeg")]
    )
    assert result["status"] == 201, result["body"]
    return result["body"][0]


def test_uploader_deletes_own_photo(
    client: TestClient, make_user, db: Session
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    photo = _uploaded(client, device["id"])

    response = client.delete(f"/photos/{photo['id']}")

    assert response.status_code == 204, response.text
    assert client.get(f"/devices/{device['id']}/photos").json() == []
    directory = settings.media_dir / f"devices/{device['id']}"
    assert not directory.exists() or not any(directory.iterdir())
    event = db.scalar(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"],
            DeviceEvent.type == "photo_removed",
        )
    )
    assert event is not None
    assert event.payload["photo_id"] == photo["id"]


def test_owner_deletes_holder_photo(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    checkout(client, device["id"], holder)
    client.cookies.clear()
    login_as(client, holder)
    photo = _uploaded(client, device["id"])

    client.cookies.clear()
    login_as(client, owner)
    response = client.delete(f"/photos/{photo['id']}")

    assert response.status_code == 204, response.text


def test_admin_deletes_any_photo(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    photo = _uploaded(client, device["id"])
    admin = register_user(make_user, username="root", role="admin")

    client.cookies.clear()
    login_as(client, admin)
    response = client.delete(f"/photos/{photo['id']}")

    assert response.status_code == 204, response.text


def test_stranger_cannot_delete_photo(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    photo = _uploaded(client, device["id"])
    stranger = register_user(make_user, username="stranger")

    client.cookies.clear()
    login_as(client, stranger)
    response = client.delete(f"/photos/{photo['id']}")

    assert response.status_code == 403, response.text
    assert response.json()["code"] == "FORBIDDEN"


def test_delete_on_archived_device_is_rejected(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    photo = _uploaded(client, device["id"])
    assert client.post(f"/devices/{device['id']}/archive").status_code == 200

    response = client.delete(f"/photos/{photo['id']}")

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "DEVICE_ARCHIVED"


def test_delete_missing_photo_is_404(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))

    response = client.delete("/photos/99999")

    assert response.status_code == 404, response.text
    assert response.json()["code"] == "NOT_FOUND"


def test_delete_succeeds_when_files_are_already_gone(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    photo = _uploaded(client, device["id"])
    for key in ("url", "thumb_url"):
        (settings.media_dir / photo[key].removeprefix("/media/")).unlink()

    response = client.delete(f"/photos/{photo['id']}")

    assert response.status_code == 204, response.text


def test_delete_photo_of_missing_device_is_404(db: Session, make_user) -> None:
    owner = make_user(username="owner")
    photo = DevicePhoto(
        device_id=999,
        file_path="devices/999/orphan.jpg",
        thumb_path="devices/999/orphan_thumb.jpg",
        uploaded_by=owner.id,
    )

    with pytest.raises(AppError) as excinfo:
        photos_service.delete_photo(db, photo, owner)

    assert excinfo.value.code == "NOT_FOUND"


def test_photo_list_requires_session(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    client.cookies.clear()

    response = client.get(f"/devices/{device['id']}/photos")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_photo_upload_requires_session(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    client.cookies.clear()

    result = upload(
        client, device["id"], [("p.jpg", image_bytes(), "image/jpeg")]
    )

    assert result["status"] == 401, result["body"]


def test_photo_list_is_newest_first(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    first = _uploaded(client, device["id"])
    second = _uploaded(client, device["id"])

    response = client.get(f"/devices/{device['id']}/photos")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [second["id"], first["id"]]


def test_photo_report_returns_attached_photos(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    report_id = client.post(
        f"/devices/{device['id']}/condition-reports", json={"condition": "ok"}
    ).json()["id"]

    result = upload(
        client,
        device["id"],
        [("p.jpg", image_bytes(), "image/jpeg")],
        report_id=str(report_id),
    )
    assert result["status"] == 201, result["body"]

    reports = client.get(f"/devices/{device['id']}/condition-reports").json()

    assert len(reports[0]["photos"]) == 1
    assert reports[0]["photos"][0]["id"] == result["body"][0]["id"]


def test_media_files_served_without_session(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    photo = _uploaded(client, device["id"])
    client.cookies.clear()

    response = client.get(photo["url"])

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")







