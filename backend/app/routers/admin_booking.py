from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import booking_service, calendar_sync_service, notification_service, webhook_service
from app.db import get_db
from app.deps import get_current_admin, require_csrf
from app.models import AdminUser

router = APIRouter(prefix="/admin/api/booking", tags=["admin-booking"], dependencies=[Depends(require_csrf)])


class RejectIn(BaseModel):
    reason: str = Field(default="", max_length=500)


class RescheduleIn(BaseModel):
    date: str
    time: str


class AdminAppointmentCreateIn(BaseModel):
    date: str
    time: str
    name: str
    email: str
    phone: str = ""
    service: str = ""
    notes: str = ""
    lang: str = "en"
    service_id: str | None = None


@router.get("/appointments")
def list_appointments(
    date_from: str | None = None, date_to: str | None = None, status_filter: str | None = None,
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    return booking_service.list_appointments(db, date_from=date_from, date_to=date_to, status=status_filter)


_CREATE_ERROR_STATUS = {
    "invalid_name": status.HTTP_400_BAD_REQUEST,
    "invalid_email": status.HTTP_400_BAD_REQUEST,
    "invalid_date": status.HTTP_400_BAD_REQUEST,
    "invalid_service": status.HTTP_400_BAD_REQUEST,
    "invalid_question": status.HTTP_400_BAD_REQUEST,
    "missing_required_answer": status.HTTP_400_BAD_REQUEST,
    "slot_unavailable": status.HTTP_409_CONFLICT,
    "already_cancelled": status.HTTP_409_CONFLICT,
    "not_found": status.HTTP_404_NOT_FOUND,
}


@router.post("/appointments")
def admin_create(
    body: AdminAppointmentCreateIn, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    """Admin-side 'Add appointment' — same validation/availability/lead-
    capture path as a public booking (booking_service.create_appointment),
    just entered by staff instead of a visitor. Still respects the slot
    grid so it can't create a double-booking; if the visitor's slot isn't
    on the grid, use a Service with no availability restriction or adjust
    availability rules rather than bypassing the check here."""
    result = booking_service.create_appointment(
        db, date_str=body.date, time_str=body.time, name=body.name, email=body.email,
        phone=body.phone, service=body.service, notes=body.notes, lang=body.lang,
        service_id=body.service_id,
    )
    if not result["ok"]:
        db.rollback()
        raise HTTPException(_CREATE_ERROR_STATUS.get(result["error"], status.HTTP_400_BAD_REQUEST), result["error"])
    db.commit()
    return result


@router.post("/appointments/{appt_id}/cancel")
def admin_cancel(appt_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    result = booking_service.admin_cancel_appointment(db, appt_id)
    db.commit()
    if not result["ok"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No appointment {appt_id!r}")
    calendar_sync_service.delete_event_for_appointment(db, appt_id)
    db.commit()
    return result


@router.post("/appointments/{appt_id}/reschedule")
def admin_reschedule(
    appt_id: str, body: RescheduleIn, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    """Admin-side edit of an existing appointment's date/time — moves it
    on the slot grid and, if a Google Calendar sync is connected,
    PATCHes the linked event to the new time in place (or creates one
    if there wasn't one yet) rather than deleting and recreating it."""
    result = booking_service.admin_reschedule_appointment(db, appt_id, body.date, body.time)
    db.commit()
    if not result["ok"]:
        raise HTTPException(_CREATE_ERROR_STATUS.get(result["error"], status.HTTP_404_NOT_FOUND), result["error"])
    notification_service.notify_booking_rescheduled(db, result["appointment"])
    webhook_service.dispatch_event(db, "booking.rescheduled", result["appointment"])
    if result["appointment"]["status"] != "pending":
        # See public_booking.py's reschedule_appointment for why this is
        # conditional on a truthy event_id, not unconditional.
        event_id = calendar_sync_service.update_event_for_appointment(db, appt_id)
        if event_id:
            result["appointment"]["external_event_id"] = event_id
    db.commit()
    return result


def _raise_for_error(error: str, appt_id: str) -> None:
    if error == "not_found":
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No appointment {appt_id!r}")
    # invalid_state: exists, but not in 'pending' — a conflict with the
    # resource's current state, not a malformed request.
    raise HTTPException(status.HTTP_409_CONFLICT, f"Appointment {appt_id!r} is not pending")


@router.post("/appointments/{appt_id}/accept")
def admin_accept(appt_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    result = booking_service.admin_accept_appointment(db, appt_id)
    db.commit()
    if not result["ok"]:
        _raise_for_error(result["error"], appt_id)
    notification_service.notify_booking_accepted(db, result["appointment"])
    webhook_service.dispatch_event(db, "booking.accepted", result["appointment"])
    event_id = calendar_sync_service.create_event_for_appointment(db, appt_id)
    if event_id:
        result["appointment"]["external_event_id"] = event_id
    db.commit()
    return result


@router.post("/appointments/{appt_id}/reject")
def admin_reject(
    appt_id: str, body: RejectIn,
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    result = booking_service.admin_reject_appointment(db, appt_id, reason=body.reason)
    db.commit()
    if not result["ok"]:
        _raise_for_error(result["error"], appt_id)
    notification_service.notify_booking_declined(db, result["appointment"], reason=body.reason)
    webhook_service.dispatch_event(db, "booking.declined", result["appointment"])
    db.commit()
    return result
