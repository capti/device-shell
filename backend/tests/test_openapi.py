import json
from pathlib import Path

from app.export_openapi import export_openapi
from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_committed_schema_matches_app() -> None:
    """Закоммиченная схема — источник типов фронтенда, она не должна отставать от кода."""
    committed = json.loads((BACKEND_DIR / "openapi.json").read_text(encoding="utf-8"))

    assert committed == create_app().openapi(), (
        "backend/openapi.json устарел: выполните `python -m app.export_openapi` "
        "и закоммитите обновлённый файл"
    )


def test_openapi_is_exported_with_auth_and_health(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"

    path = export_openapi(output)

    assert path.exists()
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert "/auth/login" in schema["paths"]
    assert "/auth/logout" in schema["paths"]
    assert "/auth/me" in schema["paths"]
    assert "/health" in schema["paths"]
    assert schema["info"]["version"]


def test_openapi_keeps_cyrillic_readable(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"

    path = export_openapi(output)

    text = path.read_text(encoding="utf-8")
    assert "\\u04" not in text


def test_openapi_contains_device_endpoints(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"

    path = export_openapi(output)

    schema = json.loads(path.read_text(encoding="utf-8"))
    assert "/devices" in schema["paths"]
    assert "/devices/{device_id}" in schema["paths"]
    assert "/devices/{device_id}/archive" in schema["paths"]
    assert "/devices/{device_id}/restore" in schema["paths"]
    assert "/devices/{device_id}/history" in schema["paths"]


def test_openapi_contains_user_endpoints(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"

    path = export_openapi(output)

    schema = json.loads(path.read_text(encoding="utf-8"))
    for endpoint in (
        "/users",
        "/users/{user_id}",
        "/users/{user_id}/deactivate",
        "/users/{user_id}/activate",
        "/users/{user_id}/password",
        "/auth/change-password",
    ):
        assert endpoint in schema["paths"], endpoint


def test_openapi_contains_rotation_endpoints(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"

    path = export_openapi(output)

    schema = json.loads(path.read_text(encoding="utf-8"))
    for endpoint in (
        "/devices/{device_id}/checkout",
        "/devices/{device_id}/return",
        "/devices/{device_id}/transfer",
        "/devices/{device_id}/owner",
        "/devices/{device_id}/status",
        "/devices/{device_id}/checkouts",
        "/devices/{device_id}/repairs",
        "/devices/{device_id}/repairs/{repair_id}/finish",
        "/devices/{device_id}/condition-reports",
    ):
        assert endpoint in schema["paths"], endpoint


def test_openapi_contains_photo_endpoints(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"

    path = export_openapi(output)

    schema = json.loads(path.read_text(encoding="utf-8"))
    assert "/devices/{device_id}/photos" in schema["paths"]
    assert "/photos/{photo_id}" in schema["paths"]


def test_openapi_contains_report_endpoints(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"

    path = export_openapi(output)

    schema = json.loads(path.read_text(encoding="utf-8"))
    for endpoint in (
        "/dashboard/stats",
        "/reports/holders",
        "/reports/overdue",
        "/reports/export.xlsx",
    ):
        assert endpoint in schema["paths"], endpoint


def test_openapi_contains_notification_endpoints(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"

    path = export_openapi(output)

    schema = json.loads(path.read_text(encoding="utf-8"))
    for endpoint in (
        "/notifications",
        "/notifications/{notification_id}/read",
        "/notifications/read-all",
    ):
        assert endpoint in schema["paths"], endpoint

