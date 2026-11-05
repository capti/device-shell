"""Схемы фотографий устройства."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.devices import UserBrief


class PhotoRead(BaseModel):
    """Сохранённая фотография с автором и ссылками на файлы."""

    model_config = ConfigDict(extra="forbid")

    id: int
    device_id: int
    report_id: int | None
    url: str
    thumb_url: str
    uploaded_by: UserBrief
    created_at: datetime
