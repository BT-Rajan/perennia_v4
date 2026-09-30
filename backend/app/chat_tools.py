"""
Tool definitions + executor the chat assistant uses to perform real
appointment actions inside the conversation — the same underlying
booking_service/notification_service/webhook_service/calendar_sync_service
calls routers/public_booking.py makes for the "Talk to Us" form's both
tabs (new booking AND manage-booking: lookup/cancel/reschedule), just
driven by tool calls instead of form fields, so a visitor who books,
looks up, cancels, or reschedules through chat gets identical
confirmations, admin alerts, webhooks, and calendar events as one who
uses the form.

Tool schemas are provider-agnostic (a plain {name, description,
parameters} dict, `parameters` being a JSON Schema object) — llm_client.py
translates this shape into whatever each provider's API expects
(Anthropic's `input_schema`, OpenAI/DeepSeek's `function.parameters`).

The executor never raises: every tool call returns a JSON-serializable
dict, even on failure (e.g. {"ok": False, "error": "slot_unavailable"}),
so a bad or stale tool call just becomes something the model can react
to and explain to the visitor, rather than crashing the whole turn.
"""
from __future__ import annotations

from typing import Any, Callable

from sqlalchemy.orm import Session

ToolExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]

BOOKING_TOOLS: list[dict[str, Any]] = [
    {
        "name": "list_services",
        "description": (
            "List the bookable services on offer, each with its duration and any custom intake "
            "questions it requires. Call this before proposing to book if you don't already know "
            "the services from earlier in the conversation."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "check_availability",
        "description": (
            "Get the real open time slots (HH:MM, 24h) for one date. Always call this before "
            "naming a specific time to the visitor — never guess, assume, or invent a time slot."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date to check, as YYYY-MM-DD."},
                "service_id": {
                    "type": "string",
                    "description": "Optional service id from list_services — narrows slots to that service's duration/buffers.",
                },
            },
            "required": ["date"],
        },
    },
    {
        "name": "book_appointment",
        "description": (
            "Actually create the appointment. Only call this once the visitor has explicitly "
            "confirmed a specific date and time that check_availability returned, and you have "
            "at least their name and email. If the chosen service has required custom questions "
            "(from list_services), collect and include those answers too."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD, matching the availability check."},
                "slot": {"type": "string", "description": "HH:MM — must be one of the times check_availability returned."},
                "name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string", "description": "Optional but preferred."},
                "service_id": {"type": "string", "description": "Optional — id from list_services."},
                "service": {
                    "type": "string",
                    "description": (
                        "Free-text description of what the visitor wants booked. Only needed if "
                        "list_services returned no services (no catalog configured) — otherwise "
                        "omit it and just pass service_id."
                    ),
                },
                "notes": {"type": "string", "description": "Optional free-text notes for the team."},
                "answers": {
                    "type": "array",
                    "description": "Answers to the chosen service's custom questions, if it has any.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question_id": {"type": "string"},
                            "answer": {"type": "string"},
                        },
                        "required": ["question_id", "answer"],
                    },
                },
            },
            "required": ["date", "slot", "name", "email"],
        },
    },
    {
        "name": "lookup_appointment",
        "description": (
            "Look up an existing appointment by its confirmation code and the email it was booked "
            "under. Call this before offering to cancel or reschedule — never guess whether an "
            "appointment exists or what its details are."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "The confirmation code, e.g. from a previous booking."},
                "email": {"type": "string", "description": "The email address the appointment was booked under."},
            },
            "required": ["id", "email"],
        },
    },
    {
        "name": "cancel_appointment",
        "description": (
            "Cancel an existing appointment. This is irreversible — only call it after the visitor "
            "has explicitly confirmed they want to cancel this specific appointment (found via "
            "lookup_appointment first), not just because they mentioned the word 'cancel'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "The confirmation code."},
                "email": {"type": "string", "description": "The email address the appointment was booked under."},
            },
            "required": ["id", "email"],
        },
    },
    {
        "name": "reschedule_appointment",
        "description": (
            "Move an existing appointment to a new date/time. Look it up first with "
            "lookup_appointment, and confirm the new slot with check_availability before calling "
            "this — never guess a time. Only call once the visitor has explicitly agreed to the "
            "specific new date and time."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "The confirmation code."},
                "email": {"type": "string", "description": "The email address the appointment was booked under."},
                "date": {"type": "string", "description": "New date, YYYY-MM-DD."},
                "slot": {"type": "string", "description": "New time, HH:MM — must be one of check_availability's results."},
            },
            "required": ["id", "email", "date", "slot"],
        },
    },
]


def _str(args: dict[str, Any], key: str) -> str:
    v = args.get(key)
    return v.strip() if isinstance(v, str) else ""


def _tool_list_services(db: Session) -> dict[str, Any]:
    from app import services_service

    return {
        "services": [
            {
                "id": s.id,
                "name": s.name,
                "duration_minutes": s.duration_minutes,
                "questions": [
                    {"id": q.id, "label": q.label, "kind": q.kind, "required": q.required}
                    for q in s.questions
                ],
            }
            for s in services_service.list_services(db, active_only=True)
        ]
    }


def _tool_check_availability(db: Session, args: dict[str, Any]) -> dict[str, Any]:
    from app import booking_service

    date_str = _str(args, "date")
    service_id = _str(args, "service_id") or None
    try:
        slots = booking_service.available_slots(db, date_str, service_id=service_id)
    except ValueError:
        return {"ok": False, "error": "invalid_date"}
    except booking_service.InvalidServiceError:
        return {"ok": False, "error": "invalid_service"}
    return {"ok": True, "date": date_str, "service_id": service_id, "slots": slots}


def _tool_book_appointment(db: Session, lang: str, args: dict[str, Any]) -> dict[str, Any]:
    from app import booking_service, calendar_sync_service, notification_service, webhook_service
    from app.settings_service import get_setting

    if not get_setting(db, "features.booking_enabled"):
        return {"ok": False, "error": "booking_disabled"}

    raw_answers = args.get("answers")
    answers = (
        [
            {"question_id": _str(a, "question_id"), "answer": _str(a, "answer")}
            for a in raw_answers
            if isinstance(a, dict)
        ]
        if isinstance(raw_answers, list)
        else []
    )

    result = booking_service.create_appointment(
        db,
        date_str=_str(args, "date"),
        time_str=_str(args, "slot"),
        name=_str(args, "name"),
        email=_str(args, "email"),
        phone=_str(args, "phone"),
        service=_str(args, "service"),
        notes=_str(args, "notes"),
        lang=lang,
        service_id=_str(args, "service_id") or None,
        answers=answers,
    )
    if not result["ok"]:
        return result

    # Mirror routers/public_booking.py's create_appointment exactly: commit
    # so the appointment is durable before firing notifications/webhooks/
    # calendar sync, then commit again since those may have touched the
    # session themselves (e.g. calendar_sync_service refreshing a token).
    db.commit()
    appt = result["appointment"]
    if appt["status"] == "pending":
        notification_service.notify_booking_requested(db, appt)
        webhook_service.dispatch_event(db, "booking.requested", appt)
    else:
        notification_service.notify_booking_confirmed(db, appt)
        webhook_service.dispatch_event(db, "booking.confirmed", appt)
        event_id = calendar_sync_service.create_event_for_appointment(db, result["id"])
        if event_id:
            appt["external_event_id"] = event_id
    db.commit()
    return result


def _tool_lookup_appointment(db: Session, args: dict[str, Any]) -> dict[str, Any]:
    from app import booking_service

    return booking_service.lookup_appointment(db, _str(args, "id"), _str(args, "email"))


def _tool_cancel_appointment(db: Session, args: dict[str, Any]) -> dict[str, Any]:
    from app import booking_service, calendar_sync_service, notification_service, webhook_service

    appt_id = _str(args, "id")
    result = booking_service.cancel_appointment(db, appt_id, _str(args, "email"))
    db.commit()
    # Mirror routers/public_booking.py's cancel_appointment exactly, so a
    # visitor cancelling through chat gets the same notifications, webhook
    # events, and calendar cleanup as one cancelling through the form.
    if result["ok"] and not result.get("already_cancelled"):
        notification_service.notify_booking_cancelled(db, result["appointment"])
        webhook_service.dispatch_event(db, "booking.cancelled", result["appointment"])
        calendar_sync_service.delete_event_for_appointment(db, appt_id)
        result["appointment"]["external_event_id"] = None
        db.commit()
    return result


def _tool_reschedule_appointment(db: Session, args: dict[str, Any]) -> dict[str, Any]:
    from app import booking_service, calendar_sync_service, notification_service, webhook_service

    appt_id = _str(args, "id")
    result = booking_service.reschedule_appointment(
        db, appt_id, _str(args, "email"), _str(args, "date"), _str(args, "slot")
    )
    db.commit()
    # Mirror routers/public_booking.py's reschedule_appointment exactly.
    if result["ok"]:
        notification_service.notify_booking_rescheduled(db, result["appointment"])
        webhook_service.dispatch_event(db, "booking.rescheduled", result["appointment"])
        if result["appointment"]["status"] != "pending":
            event_id = calendar_sync_service.update_event_for_appointment(db, appt_id)
            result["appointment"]["external_event_id"] = event_id
        else:
            calendar_sync_service.delete_event_for_appointment(db, appt_id)
            result["appointment"]["external_event_id"] = None
        db.commit()
    return result


def make_executor(db: Session, *, lang: str) -> ToolExecutor:
    """Builds a tool_executor closure bound to this request's db session
    and language — passed to llm_client.generate_reply, which calls it
    once per tool_use/tool_call the model emits."""

    def execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "list_services":
            return _tool_list_services(db)
        if name == "check_availability":
            return _tool_check_availability(db, args)
        if name == "book_appointment":
            return _tool_book_appointment(db, lang, args)
        if name == "lookup_appointment":
            return _tool_lookup_appointment(db, args)
        if name == "cancel_appointment":
            return _tool_cancel_appointment(db, args)
        if name == "reschedule_appointment":
            return _tool_reschedule_appointment(db, args)
        return {"ok": False, "error": "unknown_tool"}

    return execute
