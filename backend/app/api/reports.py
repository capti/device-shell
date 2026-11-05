"""Отчёты: дашборд, «у кого что», «просроченные» и Excel-выгрузка."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.clock import now_local
from app.db import get_db
from app.errors import AppError
from app.models import User
from app.schemas.devices import ArchivedFilter, DeviceStatus
from app.schemas.reports import DashboardCharts, DashboardStats, HoldersReport, OverdueReport
from app.services import reports as reports_service
from app.services.devices import DeviceListParams

router = APIRouter(tags=["reports"])

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@router.get("/dashboard/stats", response_model=DashboardStats)
def read_dashboard(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardStats:
    """Счётчики дашборда и топ пяти давних просрочек."""
    return DashboardStats.model_validate(reports_service.dashboard_stats(db))


@router.get("/dashboard/charts", response_model=DashboardCharts)
def read_dashboard_charts(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardCharts:
    """Агрегаты для графиков: динамика по месяцам и возраст просрочки."""
    return DashboardCharts.model_validate(reports_service.dashboard_charts(db))


@router.get("/reports/holders", response_model=HoldersReport)
def read_holders_report(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HoldersReport:
    """«У кого что»: устройство — владелец — текущий держатель."""
    return HoldersReport.model_validate(reports_service.holders_report(db))


@router.get("/reports/overdue", response_model=OverdueReport)
def read_overdue_report(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OverdueReport:
    """Просроченные устройства по единой формуле просрочки."""
    return OverdueReport.model_validate(reports_service.overdue_report(db))


@router.get("/reports/export.xlsx")
def export_xlsx(
    q: str | None = Query(default=None, max_length=128),
    status_filter: DeviceStatus | None = Query(default=None, alias="status"),
    owner_id: int | None = None,
    holder_id: int | None = None,
    overdue: bool | None = None,
    mine: bool = False,
    archived: ArchivedFilter = "false",
    from_date: date | None = None,
    to_date: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Excel «Все устройства / Просроченные / История выдач» за период."""
    from_moment, to_moment = _export_period(from_date, to_date)
    params = DeviceListParams(
        query=q,
        status=status_filter,
        owner_id=owner_id,
        holder_id=holder_id,
        overdue=overdue,
        mine=mine,
        archived=archived,
    )
    workbook = reports_service.export_workbook(
        db, viewer=user, params=params, from_date=from_moment, to_date=to_moment
    )
    filename = f"qa-export-{to_moment:%Y%m%d}.xlsx"
    return Response(
        content=reports_service.workbook_bytes(workbook),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _export_period(
    from_moment: date | None, to_moment: date | None
) -> tuple[date, date]:
    """Период для истории: по умолчанию — с начала года по сегодня."""
    today = now_local().date()
    start = from_moment or date(today.year, 1, 1)
    end = to_moment or today
    if start > end:
        raise AppError(
            "VALIDATION_ERROR",
            "Дата начала периода не может быть позже даты окончания",
            422,
        )
    return start, end
