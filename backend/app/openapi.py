"""Обогащение OpenAPI-схемы единым конвертом ошибок и бизнес-кодами отказов."""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field

ERROR_SCHEMA_REF = {"$ref": "#/components/schemas/ErrorResponse"}

AUTH_401_DESCRIPTION = (
    "Требуется вход в систему: UNAUTHORIZED, SESSION_EXPIRED, USER_INACTIVE"
)
DEFAULT_422_DESCRIPTION = "Ошибка валидации входных данных: VALIDATION_ERROR"
ORIGIN_403_DESCRIPTION = "Недопустимый источник запроса: FORBIDDEN"
ADMIN_403_DESCRIPTION = "Доступно только администратору: FORBIDDEN"
MANAGE_DEVICE_403_DESCRIPTION = (
    "Управлять устройством может только владелец или администратор: FORBIDDEN"
)
HOLD_DEVICE_403_DESCRIPTION = (
    "Действие доступно держателю, владельцу или администратору: FORBIDDEN"
)
DEVICE_404_DESCRIPTION = "Устройство не найдено: DEVICE_NOT_FOUND"
USER_404_DESCRIPTION = "Сотрудник не найден: USER_NOT_FOUND"
ARCHIVED_409_DESCRIPTION = "Устройство находится в архиве: DEVICE_ARCHIVED"


class ErrorResponse(BaseModel):
    """Единый конверт ошибок API."""

    code: str = Field(
        description="Стабильный машинный код ошибки",
        examples=["VALIDATION_ERROR"],
    )
    message: str = Field(
        description="Понятное пользователю сообщение на русском языке",
        examples=["Некорректные данные запроса"],
    )


_OPERATION_ERRORS: dict[tuple[str, str], dict[str, str]] = {
    ("/auth/login", "post"): {
        "401": "Неверный логин или пароль: INVALID_CREDENTIALS",
        "403": ORIGIN_403_DESCRIPTION,
        "429": "Превышен лимит попыток входа: RATE_LIMITED",
    },
    ("/auth/logout", "post"): {
        "403": ORIGIN_403_DESCRIPTION,
    },
    ("/auth/change-password", "post"): {
        "403": ORIGIN_403_DESCRIPTION,
        "422": (
            "Неверный текущий пароль или слабый новый пароль: "
            "INVALID_PASSWORD, WEAK_PASSWORD, VALIDATION_ERROR"
        ),
    },
    ("/users", "post"): {
        "403": ADMIN_403_DESCRIPTION,
        "409": "Логин уже занят: USERNAME_TAKEN",
        "422": "Некорректные данные или слабый пароль: VALIDATION_ERROR, WEAK_PASSWORD",
    },
    ("/users/{user_id}", "get"): {
        "404": USER_404_DESCRIPTION,
    },
    ("/users/{user_id}", "patch"): {
        "403": ADMIN_403_DESCRIPTION,
        "404": USER_404_DESCRIPTION,
        "409": "Нельзя разжаловать последнего администратора: LAST_ADMIN",
    },
    ("/users/{user_id}", "delete"): {
        "403": ORIGIN_403_DESCRIPTION,
        "405": "Физическое удаление сотрудников запрещено: METHOD_NOT_ALLOWED",
    },
    ("/users/{user_id}/deactivate", "post"): {
        "403": ADMIN_403_DESCRIPTION,
        "404": USER_404_DESCRIPTION,
        "409": (
            "У сотрудника есть устройства в обороте, он уже деактивирован или "
            "является последним администратором: HAS_DEVICES, ALREADY_INACTIVE, LAST_ADMIN"
        ),
    },
    ("/users/{user_id}/activate", "post"): {
        "403": ADMIN_403_DESCRIPTION,
        "404": USER_404_DESCRIPTION,
        "409": "Сотрудник уже активен: ALREADY_ACTIVE",
    },
    ("/users/{user_id}/password", "post"): {
        "403": ADMIN_403_DESCRIPTION,
        "404": USER_404_DESCRIPTION,
        "422": "Слишком короткий пароль: WEAK_PASSWORD, VALIDATION_ERROR",
    },
    ("/devices", "post"): {
        "403": (
            "Назначать владельцем другого сотрудника может только администратор: FORBIDDEN"
        ),
        "409": (
            "Дубликат инвентарного номера, IMEI или серийного номера: "
            "INVENTORY_TAKEN, IMEI_TAKEN, SERIAL_TAKEN, CONFLICT"
        ),
        "422": "Некорректные данные или неактивный владелец: VALIDATION_ERROR, OWNER_INACTIVE",
    },
    ("/devices/{device_id}", "get"): {
        "404": DEVICE_404_DESCRIPTION,
    },
    ("/devices/{device_id}", "patch"): {
        "403": MANAGE_DEVICE_403_DESCRIPTION,
        "404": DEVICE_404_DESCRIPTION,
        "409": (
            "Устройство в архиве или конфликт идентификаторов: "
            "DEVICE_ARCHIVED, INVENTORY_TAKEN, IMEI_TAKEN, SERIAL_TAKEN, CONFLICT"
        ),
    },
    ("/devices/{device_id}", "delete"): {
        "403": ORIGIN_403_DESCRIPTION,
        "405": "Физическое удаление устройств запрещено: METHOD_NOT_ALLOWED",
    },
    ("/devices/{device_id}/archive", "post"): {
        "403": MANAGE_DEVICE_403_DESCRIPTION,
        "404": DEVICE_404_DESCRIPTION,
        "409": (
            "У устройства есть активная выдача или оно уже в архиве: "
            "ACTIVE_CHECKOUT, ALREADY_ARCHIVED"
        ),
    },
    ("/devices/{device_id}/restore", "post"): {
        "403": MANAGE_DEVICE_403_DESCRIPTION,
        "404": DEVICE_404_DESCRIPTION,
        "409": "Устройство не находится в архиве: NOT_ARCHIVED",
        "422": (
            "Прежний владелец деактивирован или новый владелец неактивен: "
            "OWNER_REQUIRED, OWNER_INACTIVE, VALIDATION_ERROR"
        ),
    },
    ("/devices/{device_id}/history", "get"): {
        "404": DEVICE_404_DESCRIPTION,
    },
    ("/devices/{device_id}/checkout", "post"): {
        "403": MANAGE_DEVICE_403_DESCRIPTION,
        "404": DEVICE_404_DESCRIPTION,
        "409": (
            "Выдача самому себе, повторная выдача или устройство недоступно: "
            "SELF_CHECKOUT, ALREADY_CHECKED_OUT, DEVICE_ARCHIVED, DEVICE_UNAVAILABLE"
        ),
        "422": (
            "Держатель неактивен или дата возврата в прошлом: "
            "HOLDER_INACTIVE, VALIDATION_ERROR"
        ),
    },
    ("/devices/{device_id}/return", "post"): {
        "403": HOLD_DEVICE_403_DESCRIPTION,
        "404": DEVICE_404_DESCRIPTION,
        "409": "У устройства нет активной выдачи: NO_ACTIVE_CHECKOUT",
    },
    ("/devices/{device_id}/transfer", "post"): {
        "403": HOLD_DEVICE_403_DESCRIPTION,
        "404": DEVICE_404_DESCRIPTION,
        "409": (
            "Нет активной выдачи, передача тому же держателю или владельцу: "
            "NO_ACTIVE_CHECKOUT, SAME_HOLDER, SELF_CHECKOUT"
        ),
        "422": (
            "Новый держатель неактивен или дата возврата в прошлом: "
            "HOLDER_INACTIVE, VALIDATION_ERROR"
        ),
    },
    ("/devices/{device_id}/owner", "post"): {
        "403": MANAGE_DEVICE_403_DESCRIPTION,
        "404": DEVICE_404_DESCRIPTION,
        "409": ARCHIVED_409_DESCRIPTION,
        "422": "Новый владелец не найден или деактивирован: OWNER_INACTIVE, VALIDATION_ERROR",
    },
    ("/devices/{device_id}/status", "post"): {
        "403": MANAGE_DEVICE_403_DESCRIPTION,
        "404": DEVICE_404_DESCRIPTION,
        "409": (
            "Устройство в архиве или недопустимый переход статуса: "
            "DEVICE_ARCHIVED, INVALID_STATUS_TRANSITION"
        ),
        "422": (
            "Не указан комментарий при возврате потерянного устройства: "
            "COMMENT_REQUIRED, VALIDATION_ERROR"
        ),
    },
    ("/devices/{device_id}/checkouts", "get"): {
        "404": DEVICE_404_DESCRIPTION,
    },
    ("/devices/{device_id}/repairs", "get"): {
        "404": DEVICE_404_DESCRIPTION,
    },
    ("/devices/{device_id}/repairs", "post"): {
        "403": MANAGE_DEVICE_403_DESCRIPTION,
        "404": DEVICE_404_DESCRIPTION,
        "409": (
            "Устройство выдано, в архиве или недоступно для отправки в ремонт: "
            "ACTIVE_CHECKOUT, DEVICE_ARCHIVED, DEVICE_UNAVAILABLE"
        ),
    },
    ("/devices/{device_id}/repairs/{repair_id}/finish", "post"): {
        "403": MANAGE_DEVICE_403_DESCRIPTION,
        "404": "Устройство или запись ремонта не найдены: DEVICE_NOT_FOUND, REPAIR_NOT_FOUND",
        "409": "Ремонт уже завершён: REPAIR_ALREADY_FINISHED",
    },
    ("/devices/{device_id}/condition-reports", "get"): {
        "404": DEVICE_404_DESCRIPTION,
    },
    ("/devices/{device_id}/condition-reports", "post"): {
        "403": HOLD_DEVICE_403_DESCRIPTION,
        "404": DEVICE_404_DESCRIPTION,
        "409": ARCHIVED_409_DESCRIPTION,
    },
    ("/notifications/{notification_id}/read", "post"): {
        "403": ORIGIN_403_DESCRIPTION,
        "404": "Уведомление не найдено: NOTIFICATION_NOT_FOUND",
    },
    ("/notifications/read-all", "post"): {
        "403": ORIGIN_403_DESCRIPTION,
    },
    ("/devices/{device_id}/photos", "post"): {
        "403": HOLD_DEVICE_403_DESCRIPTION,
        "404": DEVICE_404_DESCRIPTION,
        "409": ARCHIVED_409_DESCRIPTION,
        "422": (
            "Превышен лимит 5 фото, размер 10 МБ, неверный формат или чужой отчёт: "
            "PHOTO_LIMIT, PHOTO_TOO_LARGE, UNSUPPORTED_FORMAT, REPORT_DEVICE_MISMATCH, "
            "VALIDATION_ERROR"
        ),
    },
    ("/devices/{device_id}/photos", "get"): {
        "404": DEVICE_404_DESCRIPTION,
    },
    ("/photos/{photo_id}", "delete"): {
        "403": "Удалять фото может автор, владелец или администратор: FORBIDDEN",
        "404": "Фото или устройство не найдено: NOT_FOUND",
        "409": ARCHIVED_409_DESCRIPTION,
    },
    ("/dashboard/stats", "get"): {
        "403": ADMIN_403_DESCRIPTION,
    },
    ("/dashboard/charts", "get"): {
        "403": ADMIN_403_DESCRIPTION,
    },
    ("/audit/events", "get"): {
        "403": ADMIN_403_DESCRIPTION,
    },
    ("/audit/logins", "get"): {
        "403": ADMIN_403_DESCRIPTION,
    },
}


def _error_response(description: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {"application/json": {"schema": ERROR_SCHEMA_REF}},
    }


def _enrich_operation(path: str, method: str, operation: dict[str, Any]) -> None:
    responses = operation["responses"]
    if "security" in operation:
        responses["401"] = _error_response(AUTH_401_DESCRIPTION)
    if "422" in responses:
        responses["422"] = _error_response(DEFAULT_422_DESCRIPTION)
    for status_code, description in _OPERATION_ERRORS.get((path, method), {}).items():
        responses[status_code] = _error_response(description)


def build_openapi(app: FastAPI) -> dict[str, Any]:
    """Строит схему OpenAPI с единым конвертом `ErrorResponse` и бизнес-кодами ошибок."""
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schemas = schema["components"]["schemas"]
    schemas.pop("HTTPValidationError", None)
    schemas.pop("ValidationError", None)
    schemas["ErrorResponse"] = ErrorResponse.model_json_schema()

    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            _enrich_operation(path, method, operation)
    return schema
