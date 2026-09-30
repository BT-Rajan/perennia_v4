from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_admin, require_csrf
from app.models import AdminUser

router = APIRouter(prefix="/admin/api/availability", tags=["admin-availability"], dependencies=[Depends(require_csrf)])


# ── Schemas ──────────────────────────────────────────────────────────

class RuleOut(BaseModel):
    id: str
    service_id: str | None
    kind: str
    weekday: int | None
    date: str | None
    start_time: str | None
    end_time: str | None
    is_closed: bool


class RuleCreateIn(BaseModel):
    service_id: str | None = None
    kind: str
    weekday: int | None = Field(default=None, ge=0, le=6)
    date: str | None = Field(default=None, max_length=10)
    start_time: str | None = Field(default=None, max_length=5)
    end_time: str | None = Field(default=None, max_length=5)
    is_closed: bool = False


class RuleUpdateIn(BaseModel):
    weekday: int | None = Field(default=None, ge=0, le=6)
    date: str | None = Field(default=None, max_length=10)
    start_time: str | None = Field(default=None, max_length=5)
    end_time: str | None = Field(default=None, max_length=5)
    is_closed: bool | None = None


class EffectiveRangeOut(BaseModel):
    start: str
    end: str


class EffectiveOut(BaseModel):
    is_closed: bool
    source: str  # "rule" | "legacy_settings"
    ranges: list[EffectiveRangeOut]


def _rule_dict(r) -> dict[str, Any]:
    return dict(id=r.id, service_id=r.service_id, kind=r.kind, weekday=r.weekday, date=r.date,
                start_time=r.start_time, end_time=r.end_time, is_closed=r.is_closed)


def _error_status(message: str) -> int:
    # "Overlaps existing rule ..." is a conflict with another resource;
    # everything else here is a malformed request.
    return status.HTTP_409_CONFLICT if message.startswith("Overlaps") else status.HTTP_400_BAD_REQUEST


# ── Rules ────────────────────────────────────────────────────────────

@router.get("/rules", response_model=list[RuleOut])
def list_rules(
    service_id: str | None = None,
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    from app import availability_service
    return [RuleOut(**_rule_dict(r)) for r in availability_service.list_rules(db, service_id=service_id)]


@router.post("/rules", response_model=RuleOut)
def create_rule(body: RuleCreateIn, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import availability_service
    try:
        rule = availability_service.create_rule(
            db, service_id=body.service_id, kind=body.kind, weekday=body.weekday, date=body.date,
            start_time=body.start_time, end_time=body.end_time, is_closed=body.is_closed,
            actor_id=admin.id, actor_username=admin.username,
        )
        db.commit()
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(_error_status(str(e)), str(e))
    db.refresh(rule)
    return RuleOut(**_rule_dict(rule))


@router.patch("/rules/{rule_id}", response_model=RuleOut)
def update_rule(
    rule_id: str, body: RuleUpdateIn,
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    from app import availability_service
    try:
        rule = availability_service.update_rule(
            db, rule_id, weekday=body.weekday, date=body.date, start_time=body.start_time,
            end_time=body.end_time, is_closed=body.is_closed, actor_id=admin.id, actor_username=admin.username,
        )
        db.commit()
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(_error_status(str(e)), str(e))
    db.refresh(rule)
    return RuleOut(**_rule_dict(rule))


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import availability_service
    ok = availability_service.delete_rule(db, rule_id, actor_id=admin.id, actor_username=admin.username)
    db.commit()
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No availability rule {rule_id!r}")
    return {"ok": True}


# ── Preview ──────────────────────────────────────────────────────────

@router.get("/effective", response_model=EffectiveOut)
def effective(
    date: str, service_id: str | None = None,
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    """Debugging/preview endpoint: what hours will this service
    actually have on this date, after applying every applicable rule's
    precedence — so an admin can verify "what does Tuesday look like"
    without reading raw rule rows."""
    from app import availability_service
    try:
        d = dt.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid date")

    ranges = availability_service.effective_ranges(db, service_id=service_id, weekday=d.weekday(), date_str=date)
    if ranges is None:
        # No AvailabilityRule exists anywhere yet — mirror
        # booking_service.py's own legacy fallback exactly, so this
        # preview matches what a real booking request would see.
        from app.settings_service import get_setting
        workdays = set(get_setting(db, "booking.workdays"))
        start_h, end_h = get_setting(db, "booking.day_start_hour"), get_setting(db, "booking.day_end_hour")
        if d.weekday() not in workdays or end_h <= start_h:
            return EffectiveOut(is_closed=True, source="legacy_settings", ranges=[])
        return EffectiveOut(
            is_closed=False, source="legacy_settings",
            ranges=[EffectiveRangeOut(start=f"{start_h:02d}:00", end=f"{end_h:02d}:00")],
        )
    if not ranges:
        return EffectiveOut(is_closed=True, source="rule", ranges=[])
    return EffectiveOut(
        is_closed=False, source="rule",
        ranges=[EffectiveRangeOut(start=f"{s // 60:02d}:{s % 60:02d}", end=f"{e // 60:02d}:{e % 60:02d}") for s, e in ranges],
    )
