from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_admin, require_csrf
from app.google_calendar_client import GoogleCalendarError
from app.models import AdminUser

router = APIRouter(prefix="/admin/api/calendar-events", tags=["admin-calendar-events"], dependencies=[Depends(require_csrf)])


class EventOut(BaseModel):
    id: str
    summary: str
    description: str = ""
    start: str | None = None
    end: str | None = None
    all_day: bool = False
    html_link: str | None = None


class EventIn(BaseModel):
    summary: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=2000)
    start: str  # ISO datetime, e.g. 2026-08-20T14:00:00
    end: str
    timezone: str = "UTC"


def _handle_not_configured_or_google_error(e: Exception) -> None:
    from app import calendar_sync_service
    if isinstance(e, calendar_sync_service.CalendarSyncNotConfigured):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    if isinstance(e, GoogleCalendarError):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e))
    raise


@router.get("", response_model=list[EventOut])
def list_events(
    date_from: str = Query(..., description="ISO date, e.g. 2026-08-01"),
    date_to: str = Query(..., description="ISO date, e.g. 2026-08-31"),
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    """Every event on the connected calendar in the window — this is
    the whole calendar, not just events this app created for a booking,
    since the point of this screen is full manual control."""
    from app import calendar_sync_service
    try:
        time_min = dt.datetime.fromisoformat(date_from).replace(tzinfo=dt.timezone.utc)
        time_max = dt.datetime.fromisoformat(date_to).replace(tzinfo=dt.timezone.utc) + dt.timedelta(days=1)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "date_from/date_to must be ISO dates")
    try:
        return calendar_sync_service.list_manual_events(db, time_min=time_min, time_max=time_max)
    except Exception as e:
        _handle_not_configured_or_google_error(e)


@router.post("", response_model=EventOut)
def create_event(body: EventIn, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import calendar_sync_service
    try:
        result = calendar_sync_service.create_manual_event(
            db, summary=body.summary, description=body.description, start_iso=body.start, end_iso=body.end,
            timezone=body.timezone, actor_id=admin.id, actor_username=admin.username,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        _handle_not_configured_or_google_error(e)
        raise
    return EventOut(id=result["id"], summary=body.summary, description=body.description,
                     start=body.start, end=body.end)


@router.patch("/{event_id}", response_model=EventOut)
def update_event(event_id: str, body: EventIn, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import calendar_sync_service
    try:
        calendar_sync_service.update_manual_event(
            db, event_id, summary=body.summary, description=body.description, start_iso=body.start,
            end_iso=body.end, timezone=body.timezone, actor_id=admin.id, actor_username=admin.username,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        _handle_not_configured_or_google_error(e)
        raise
    return EventOut(id=event_id, summary=body.summary, description=body.description,
                     start=body.start, end=body.end)


@router.delete("/{event_id}")
def delete_event(event_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import calendar_sync_service
    try:
        calendar_sync_service.delete_manual_event(db, event_id, actor_id=admin.id, actor_username=admin.username)
        db.commit()
    except Exception as e:
        db.rollback()
        _handle_not_configured_or_google_error(e)
        raise
    return {"ok": True}
