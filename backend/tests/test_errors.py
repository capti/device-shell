from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.errors import _validation_message
from app.main import app


class _Payload(BaseModel):
    name: str


@app.post("/_test/validate")
def _validate(payload: _Payload) -> _Payload:
    return payload


@app.get("/_test/http-error-dict")
def _http_error_dict() -> None:
    raise HTTPException(status_code=400, detail={"field": "name"})


@app.get("/_test/boom")
def _boom() -> None:
    raise RuntimeError("boom")


def test_not_found_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/missing-endpoint")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["message"]
    assert "detail" not in body


def test_validation_error_uses_error_envelope(client: TestClient) -> None:
    response = client.post("/_test/validate", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "name" in body["message"]
    assert "detail" not in body


def test_http_exception_with_non_string_detail_uses_default_message(
    client: TestClient,
) -> None:
    response = client.get("/_test/http-error-dict")

    assert response.status_code == 400
    assert response.json() == {
        "code": "BAD_REQUEST",
        "message": "Некорректный запрос",
    }


def test_unhandled_exception_uses_error_envelope(caplog) -> None:
    with TestClient(app, raise_server_exceptions=False) as local_client:
        response = local_client.get("/_test/boom")

    logged = next(
        record for record in caplog.records if "Необработанная ошибка" in record.message
    )
    assert logged.exc_info is not None
    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "code": "INTERNAL_ERROR",
        "message": "Внутренняя ошибка сервера",
    }
    assert "boom" not in response.text
    assert "RuntimeError" not in response.text


def test_app_error_uses_error_envelope() -> None:
    from fastapi.testclient import TestClient

    from app.errors import AppError

    @app.get("/_test/app-error")
    def _app_error() -> None:
        raise AppError("ACTIVE_CHECKOUT", "Устройство выдано", 409)

    with TestClient(app) as local_client:
        response = local_client.get("/_test/app-error")

    assert response.status_code == 409
    assert response.json() == {
        "code": "ACTIVE_CHECKOUT",
        "message": "Устройство выдано",
    }


def test_validation_message_empty_errors_uses_default() -> None:
    assert (
        _validation_message(RequestValidationError([]))
        == "Некорректные данные запроса"
    )

