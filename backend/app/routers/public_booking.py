from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import booking_service, calendar_sync_service, notification_service, webhook_service
from app.config import settings
from app.db import get_db
from app.rate_limit import limiter
from app.settings_service import get_setting

router = APIRouter(prefix="/api/booking", tags=["public-booking"])


class AnswerIn(BaseModel):
    question_id: str
    answer: str = Field(default="", max_length=2000)


class CreateAppointmentRequest(BaseModel):
    date: str
    slot: str
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    phone: str = Field(default="", max_length=40)
    service: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=1000)
    lang: str = Field(default="en", max_length=8)
    service_id: str | None = None
    answers: list[AnswerIn] = Field(default_factory=list)


class LookupRequest(BaseModel):
    id: str = Field(max_length=16)
    email: str = Field(max_length=254)


class CancelRequest(BaseModel):
    id: str = Field(max_length=16)
    email: str = Field(max_length=254)


class RescheduleRequest(BaseModel):
    id: str = Field(max_length=16)
    email: str = Field(max_length=254)
    date: str
    time: str


@router.get("/services")
def list_services(db: Session = Depends(get_db)):
    """Active services only — a service becomes visible here the moment
    an admin activates it (services_service.py), with no
    features.booking_enabled gate: browsing what's offered is harmless
    even while booking itself is switched off."""
    from app import services_service
    return [
        {
            "id": s.id, "name": s.name, "slug": s.slug, "duration_minutes": s.duration_minutes,
            "location_type": s.location_type,
            "questions": [
                {"id": q.id, "kind": q.kind, "label": q.label, "required": q.required}
                for q in s.questions
            ],
        }
        for s in services_service.list_services(db, active_only=True)
    ]


@router.get("/slots")
def get_slots(date: str, service_id: str | None = None, db: Session = Depends(get_db)):
    if not get_setting(db, "features.booking_enabled"):
        return {"slots": []}
    try:
        slots = booking_service.available_slots(db, date, service_id=service_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid date")
    except booking_service.InvalidServiceError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown or inactive service")
    # Otherwise read-only, but Pass 12's calendar sync can refresh and
    # cache a Google access token as a side effect of computing these
    # slots (calendar_sync_service._ensure_fresh_access_token) — commit
    # so that refresh is actually persisted rather than silently
    # discarded when this session closes, which would otherwise force
    # a fresh token refresh on every single slots request.
    db.commit()
    return {"slots": slots}


@router.post("/appointments")
@limiter.limit(settings.RATE_LIMIT_APPOINTMENT)
def create_appointment(request: Request, body: CreateAppointmentRequest, db: Session = Depends(get_db)):
    if not get_setting(db, "features.booking_enabled"):
        return {"ok": False, "error": "booking_disabled"}
    result = booking_service.create_appointment(
        db, date_str=body.date, time_str=body.slot, name=body.name, email=body.email,
        phone=body.phone, service=body.service, notes=body.notes, lang=body.lang,
        service_id=body.service_id, answers=[a.model_dump() for a in body.answers],
    )
    db.commit()
    if result["ok"]:
        if result["appointment"]["status"] == "pending":
            notification_service.notify_booking_requested(db, result["appointment"])
            webhook_service.dispatch_event(db, "booking.requested", result["appointment"])
        else:
            notification_service.notify_booking_confirmed(db, result["appointment"])
            webhook_service.dispatch_event(db, "booking.confirmed", result["appointment"])
            event_id = calendar_sync_service.create_event_for_appointment(db, result["id"])
            if event_id:
                result["appointment"]["external_event_id"] = event_id
        db.commit()  # notification/webhook/calendar-sync activity may have touched the session
    return result


@router.post("/appointments/lookup")
@limiter.limit(settings.RATE_LIMIT_LOOKUP)
def lookup_appointment(request: Request, body: LookupRequest, db: Session = Depends(get_db)):
    return booking_service.lookup_appointment(db, body.id, body.email)


@router.post("/appointments/cancel")
@limiter.limit(settings.RATE_LIMIT_APPOINTMENT)
def cancel_appointment(request: Request, body: CancelRequest, db: Session = Depends(get_db)):
    result = booking_service.cancel_appointment(db, body.id, body.email)
    db.commit()
    if result["ok"] and not result.get("already_cancelled"):
        notification_service.notify_booking_cancelled(db, result["appointment"])
        webhook_service.dispatch_event(db, "booking.cancelled", result["appointment"])
        calendar_sync_service.delete_event_for_appointment(db, body.id)
        result["appointment"]["external_event_id"] = None
        db.commit()
    return result


@router.post("/appointments/reschedule")
@limiter.limit(settings.RATE_LIMIT_APPOINTMENT)
def reschedule_appointment(request: Request, body: RescheduleRequest, db: Session = Depends(get_db)):
    result = booking_service.reschedule_appointment(db, body.id, body.email, body.date, body.time)
    db.commit()
    if result["ok"]:
        notification_service.notify_booking_rescheduled(db, result["appointment"])
        webhook_service.dispatch_event(db, "booking.rescheduled", result["appointment"])
        if result["appointment"]["status"] != "pending":
            # PATCHes the existing Google event to the new time in place
            # (falls back to creating one if there wasn't one already) —
            # keeps the same event id and anything attached to it on
            # Google's side, instead of the old delete-then-recreate.
            # None means the push failed without changing anything (see
            # update_event_for_appointment's docstring — a non-404
            # failure deliberately leaves the existing link alone rather
            # than risking a duplicate) - only overwrite the response
            # when there's an actual new value to report, so a
            # transient failure doesn't make an appointment that's
            # still correctly linked in the database look unlinked to
            # the client.
            event_id = calendar_sync_service.update_event_for_appointment(db, body.id)
            if event_id:
                result["appointment"]["external_event_id"] = event_id
        else:
            calendar_sync_service.delete_event_for_appointment(db, body.id)
            result["appointment"]["external_event_id"] = None
        db.commit()
    return result
