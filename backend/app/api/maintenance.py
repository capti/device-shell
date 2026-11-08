"""Эндпоинты обслуживания: журнал ремонтов и отчёты о состоянии."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.photos import _photo_read
from app.api.serializers import user_brief, users_by_id
from app.db import get_db
from app.models import ConditionReport, Repair, User
from app.schemas.maintenance import (
    ConditionReportCreate,
    ConditionReportRead,
    RepairCreate,
    RepairFinishRequest,
    RepairRead,
)
from app.services import condition_reports as reports_service
from app.services import devices as devices_service
from app.services import maintenance
from app.services import photos as photos_service

router = APIRouter(prefix="/devices", tags=["maintenance"])


def _creator(users: dict[int, User], user_id: int | None):
    user = users.get(user_id) if user_id is not None else None
    return user_brief(user) if user is not None else None


def _repair_read(repair: Repair, users: dict[int, User]) -> RepairRead:
    return RepairRead(
        id=repair.id,
        device_id=repair.device_id,
        sent_at=repair.sent_at,
        returned_at=repair.returned_at,
        service=repair.service,
        description=repair.description,
        cost=repair.cost,
        comment=repair.comment,
        created_by=_creator(users, repair.created_by),
    )


def _repair_list(db: Session, repairs: Sequence[Repair]) -> list[RepairRead]:
    users = users_by_id(db, [repair.created_by for repair in repairs])
    return [_repair_read(repair, users) for repair in repairs]


def _report_read(
    report: ConditionReport, users: dict[int, User], photos: dict
) -> ConditionReportRead:
    return ConditionReportRead(
        id=report.id,
        device_id=report.device_id,
        checkout_id=report.checkout_id,
        author=user_brief(users[report.author_id]),
        condition=report.condition,
        requires_repair=report.requires_repair,
        comment=report.comment,
        photos=[
            _photo_read(photo, users)
            for photo in photos.get(report.id, [])
        ],
        created_at=report.created_at,
    )


def _report_list(
    db: Session, reports: Sequence[ConditionReport]
) -> list[ConditionReportRead]:
    if not reports:
        return []
    users = users_by_id(db, [report.author_id for report in reports])
    device_id = reports[0].device_id
    photos = photos_service.photos_by_report(db, device_id)
    users.update(
        users_by_id(db, [photo.uploaded_by for group in photos.values() for photo in group])
    )
    return [_report_read(report, users, photos) for report in reports]


@router.get("/{device_id}/repairs", response_model=list[RepairRead])
def read_repairs(
    device_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RepairRead]:
    """Журнал ремонтов устройства в порядке от новых к старым."""
    devices_service.get_device(db, device_id)
    return _repair_list(db, maintenance.list_repairs(db, device_id))


@router.post(
    "/{device_id}/repairs",
    response_model=RepairRead,
    status_code=status.HTTP_201_CREATED,
)
def start_repair(
    device_id: int,
    payload: RepairCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RepairRead:
    """Отправка активного устройства в ремонт с переводом в статус `repair`."""
    device = devices_service.get_device(db, device_id)
    repair = maintenance.start_repair(db, device, payload, user)
    return _repair_list(db, [repair])[0]


@router.post("/{device_id}/repairs/{repair_id}/finish", response_model=RepairRead)
def finish_repair(
    device_id: int,
    repair_id: int,
    payload: RepairFinishRequest | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RepairRead:
    """Завершение ремонта устройства с возвратом статуса в `active`."""
    device = devices_service.get_device(db, device_id)
    repair = maintenance.finish_repair(
        db, device, repair_id, payload or RepairFinishRequest(), user
    )
    return _repair_list(db, [repair])[0]


@router.get("/{device_id}/condition-reports", response_model=list[ConditionReportRead])
def read_condition_reports(
    device_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConditionReportRead]:
    """Список отчётов о состоянии устройства вместе с прикреплёнными фотографиями."""
    devices_service.get_device(db, device_id)
    return _report_list(db, reports_service.list_reports(db, device_id))


@router.post(
    "/{device_id}/condition-reports",
    response_model=ConditionReportRead,
    status_code=status.HTTP_201_CREATED,
)
def create_condition_report(
    device_id: int,
    payload: ConditionReportCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConditionReportRead:
    """Добавление отчёта о состоянии устройства держателем, владельцем или администратором."""
    device = devices_service.get_device(db, device_id)
    report = reports_service.submit_report(db, device, payload, user)
    return _report_list(db, [report])[0]
