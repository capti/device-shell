from datetime import timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Checkout, ConditionReport, DevicePhoto, Repair


def test_condition_report_with_photo_and_repair(
    db: Session, make_user, make_device
) -> None:
    owner = make_user(username="owner")
    holder = make_user(username="holder")
    device = make_device(owner=owner)

    now = now_local()
    checkout = Checkout(
        device_id=device.id,
        user_id=holder.id,
        taken_at=now,
        expected_return_at=now + timedelta(days=14),
    )
    db.add(checkout)
    db.commit()

    report = ConditionReport(
        device_id=device.id,
        checkout_id=checkout.id,
        author_id=holder.id,
        condition="scratches",
        requires_repair=True,
        comment="Царапина на корпусе",
    )
    db.add(report)
    db.commit()

    photo = DevicePhoto(
        device_id=device.id,
        report_id=report.id,
        file_path="devices/1/photo.jpg",
        thumb_path="devices/1/photo_thumb.jpg",
        uploaded_by=holder.id,
    )
    repair = Repair(
        device_id=device.id,
        sent_at=now,
        service="Сервис-центр",
        description="Замена экрана",
        cost=Decimal("12000.00"),
        created_by=owner.id,
    )
    db.add_all([photo, repair])
    db.commit()

    assert report.id is not None
    assert photo.report_id == report.id
    assert repair.device_id == device.id
    assert repair.cost == Decimal("12000.00")


def test_photo_can_exist_without_report(db: Session, make_user, make_device) -> None:
    owner = make_user()
    device = make_device(owner=owner)

    photo = DevicePhoto(
        device_id=device.id,
        file_path="devices/1/free.jpg",
        thumb_path="devices/1/free_thumb.jpg",
        uploaded_by=owner.id,
    )
    db.add(photo)
    db.commit()

    assert photo.id is not None
    assert photo.report_id is None
