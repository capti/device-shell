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


def test_openapi_uses_unified_error_response_without_http_validation_error() -> None:
    schema = create_app().openapi()
    schemas = schema["components"]["schemas"]

    assert "ErrorResponse" in schemas
    assert set(schemas["ErrorResponse"]["required"]) == {"code", "message"}
    assert "HTTPValidationError" not in schemas
    assert "ValidationError" not in schemas

    error_ref = {"$ref": "#/components/schemas/ErrorResponse"}
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            for status_code, response in operation["responses"].items():
                if status_code.startswith("4"):
                    content = response["content"]["application/json"]
                    assert content["schema"] == error_ref, (
                        f"{method.upper()} {path} -> {status_code}"
                    )


def test_openapi_declares_cookie_security_scheme_and_protected_operations() -> None:
    schema = create_app().openapi()
    security_schemes = schema["components"]["securitySchemes"]

    assert "SessionCookie" in security_schemes
    cookie_scheme = security_schemes["SessionCookie"]
    assert cookie_scheme["type"] == "apiKey"
    assert cookie_scheme["in"] == "cookie"
    assert cookie_scheme["name"] == "qa_session"

    public_ops = {
        ("/health", "get"),
        ("/auth/login", "post"),
        ("/auth/logout", "post"),
    }
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            if (path, method) in public_ops:
                assert "security" not in operation, f"{method.upper()} {path}"
            else:
                assert operation.get("security") == [{"SessionCookie": []}], (
                    f"{method.upper()} {path}"
                )
                assert "401" in operation["responses"], f"{method.upper()} {path}"
                assert "UNAUTHORIZED" in operation["responses"]["401"]["description"]


def test_openapi_declares_business_error_codes_in_responses() -> None:
    schema = create_app().openapi()
    paths = schema["paths"]

    archive_409 = paths["/devices/{device_id}/archive"]["post"]["responses"]["409"]
    assert "ACTIVE_CHECKOUT" in archive_409["description"]

    checkout_409 = paths["/devices/{device_id}/checkout"]["post"]["responses"]["409"]
    assert "SELF_CHECKOUT" in checkout_409["description"]
    assert "ALREADY_CHECKED_OUT" in checkout_409["description"]

    deactivate_409 = paths["/users/{user_id}/deactivate"]["post"]["responses"]["409"]
    assert "HAS_DEVICES" in deactivate_409["description"]
    assert "LAST_ADMIN" in deactivate_409["description"]

    create_user_403 = paths["/users"]["post"]["responses"]["403"]
    assert "FORBIDDEN" in create_user_403["description"]

    login_429 = paths["/auth/login"]["post"]["responses"]["429"]
    assert "RATE_LIMITED" in login_429["description"]


def test_openapi_has_descriptions_for_all_operations() -> None:
    schema = create_app().openapi()
    operations = [
        (path, method, operation.get("description", ""))
        for path, methods in schema["paths"].items()
        for method, operation in methods.items()
    ]

    assert len(operations) == 45
    missing = [
        f"{method.upper()} {path}"
        for path, method, description in operations
        if not description.strip()
    ]
    assert missing == []


