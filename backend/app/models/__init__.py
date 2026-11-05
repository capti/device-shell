"""ORM-модели. Импорт пакета регистрирует все таблицы в `Base.metadata`."""

from app.models.audit import DeviceEvent
from app.models.checkouts import Checkout
from app.models.devices import Device
from app.models.login_events import LoginEvent
from app.models.notifications import Notification
from app.models.reports import ConditionReport, DevicePhoto, Repair
from app.models.sessions import UserSession
from app.models.users import User

__all__ = [
    "Checkout",
    "ConditionReport",
    "Device",
    "DeviceEvent",
    "DevicePhoto",
    "LoginEvent",
    "Notification",
    "Repair",
    "User",
    "UserSession",
]
