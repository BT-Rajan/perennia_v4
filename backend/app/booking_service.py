"""
Booking business logic. Timezone, notice window, and how far ahead you
can book still come from the booking.* settings registry
(app/settings_registry.py), read fresh on every call. As of Pass 9
(docs/CALENDAR_MODULE_PLAN.md), *which hours are open* comes from
AvailabilityRule (app/availability_service.py) instead of the old
booking.workdays/day_start_hour/day_end_hour trio — unless no
AvailabilityRule exists anywhere yet, in which case those settings are
still used exactly as before, so an install that predates Pass 9 (or
simply hasn't touched Availability) keeps behaving identically.

Pass 8 adds what a *service* contributes on top of the day's open
hours: its own duration and buffer time. A booking's service_id is
optional — a site that has never defined a Service occupies one
booking.slot_minutes-sized grid slot with no buffer. When a service is
given, slot generation still snaps to the same booking.slot_minutes
grid (so times stay predictable and stable across services) but each
candidate slot's *occupied span* is the service's own duration plus its
buffers, checked for overlap against every other booking that day
(rather than an exact-time-string match, which only ever worked because
every booking used to be the same length).
"""
from __future__ import annotations

import datetime as dt
import re
import secrets
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Appointment, AppointmentQuestionAnswer, Service
from app.settings_service import get_setting

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # no 0/O/1/I — avoids lookalike confusion


class InvalidServiceError(Exception):
    """Raised when a service_id is given but doesn't resolve to an
    active Service. Deliberately not a ValueError — available_slots
    already uses ValueError for "the date string was malformed," and
    callers need to tell the two apart to return the right error code."""


def _booking_config(db: Session) -> dict:
    return {
        "timezone": get_setting(db, "booking.timezone"),
        "slot_minutes": get_setting(db, "booking.slot_minutes"),
        "day_start_hour": get_setting(db, "booking.day_start_hour"),
        "day_end_hour": get_setting(db, "booking.day_end_hour"),
        "workdays": set(get_setting(db, "booking.workdays")),
        "max_days_ahead": get_setting(db, "booking.max_days_ahead"),
        "min_notice_hours": get_setting(db, "booking.min_notice_hours"),
        "pending_expiry_hours": get_setting(db, "booking.pending_expiry_hours"),
    }


def _now(cfg: dict) -> dt.datetime:
    return dt.datetime.now(ZoneInfo(cfg["timezone"]))


def _pending_cutoff(cfg: dict) -> dt.datetime | None:
    """None means disabled (booking.pending_expiry_hours == 0) — a
    pending appointment holds its slot indefinitely, as it always did
    before this setting existed. Otherwise, the UTC instant a pending
    appointment's created_at has to be older than to stop counting as
    blocking / become eligible for auto-decline. Absolute elapsed time,
    not business-local wall-clock, so this is intentionally independent
    of booking.timezone."""
    hours = cfg["pending_expiry_hours"]
    if not hours:
        return None
    return dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)


def _time_to_minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _as_utc(value: dt.datetime) -> dt.datetime:
    """Some dialects (SQLite, used in dev/tests) don't round-trip tzinfo
    on a DateTime(timezone=True) column — reads back naive. Normalize
    before comparing against a tz-aware cutoff; same reasoning as
    calendar_sync_service.py's _ensure_fresh_access_token."""
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value


def _resolve_service(db: Session, service_id: str | None) -> Service | None:
    if service_id is None:
        return None
    service = db.get(Service, service_id)
    if service is None or not service.is_active:
        raise InvalidServiceError(service_id)
    return service


def _duration_and_buffers(cfg: dict, service: Service | None) -> tuple[int, int, int]:
    """(duration_minutes, buffer_before, buffer_after). No service ->
    the pre-Pass-8 default: one grid slot, no buffer."""
    if service is None:
        return cfg["slot_minutes"], 0, 0
    return service.duration_minutes, service.buffer_before_minutes, service.buffer_after_minutes


def _day_ranges(db: Session, cfg: dict, date: dt.date, service_id: str | None) -> list[tuple[int, int]]:
    """Open (start_minutes, end_minutes) ranges for this date, resolved
    through availability_service.effective_ranges. Falls back to the
    legacy single-range booking.workdays/day_start_hour/day_end_hour
    settings when no AvailabilityRule exists anywhere yet — see that
    function's docstring and the module docstring above."""
    from app import availability_service
    ranges = availability_service.effective_ranges(
        db, service_id=service_id, weekday=date.weekday(), date_str=date.isoformat()
    )
    if ranges is not None:
        return ranges
    if date.weekday() not in cfg["workdays"]:
        return []
    if cfg["day_end_hour"] <= cfg["day_start_hour"]:
        return []  # inconsistent hours - treat as closed rather than erroring
    return [(cfg["day_start_hour"] * 60, cfg["day_end_hour"] * 60)]


def _grid_slots_for_ranges(cfg: dict, ranges: list[tuple[int, int]]) -> list[str]:
    """Candidate start times on the booking.slot_minutes grid, across
    every open range for the day (a split day — e.g. 09:00-12:00 and
    13:00-17:00 — just means two ranges, each gridded independently;
    duplicates across overlapping ranges are deduped defensively)."""
    seen: set[str] = set()
    slots: list[str] = []
    for start_min, end_min in ranges:
        t = start_min
        while t < end_min:
            hh, mm = divmod(t, 60)
            s = f"{hh:02d}:{mm:02d}"
            if s not in seen:
                seen.add(s)
                slots.append(s)
            t += cfg["slot_minutes"]
    slots.sort()
    return slots


def _fits_in_ranges(start_min: int, end_min: int, ranges: list[tuple[int, int]]) -> bool:
    return any(r_start <= start_min and end_min <= r_end for r_start, r_end in ranges)


def _booked_intervals(db: Session, cfg: dict, date_str: str, *, exclude_id: str | None = None) -> list[tuple[int, int]]:
    """Each confirmed *or pending* appointment that day, as a
    (start, end) range in minutes-from-midnight, already expanded by
    *that appointment's own* service buffers (or the legacy
    single-slot default if it has none). A later slot's own buffer is
    applied separately by the caller, so two adjacent bookings each get
    their own buffer honored rather than only one side of the gap
    being protected.

    Pending holds the slot on purpose (Pass 10,
    docs/CALENDAR_MODULE_PLAN.md / PASS10_NOTES.md): the alternative —
    a second visitor booking the same slot while the first request
    awaits organizer approval — is a worse failure mode for a small
    business than a slot looking briefly unavailable. But only up to
    booking.pending_expiry_hours old (_pending_cutoff) — past that, an
    admin has had a full expiry window to act and didn't, so this stops
    counting it as blocking even before the background sweep
    (expire_stale_pending_appointments) gets around to formally
    declining it. Checked here, live, rather than only relying on that
    sweep's cadence, so availability is correct immediately rather than
    only eventually."""
    cutoff = _pending_cutoff(cfg)
    stmt = select(Appointment).where(Appointment.date == date_str, Appointment.status.in_(("confirmed", "pending")))
    intervals = []
    for appt in db.scalars(stmt):
        if appt.id == exclude_id:
            continue
        if appt.status == "pending" and cutoff is not None and _as_utc(appt.created_at) < cutoff:
            continue
        service = db.get(Service, appt.service_id) if appt.service_id else None
        duration, buf_before, buf_after = _duration_and_buffers(cfg, service)
        start = _time_to_minutes(appt.time)
        intervals.append((start - buf_before, start + duration + buf_after))
    return intervals


class CalendarSyncUnavailableError(Exception):
    """Raised internally when calendar sync is enabled, connected, and
    the Google API call failed, AND booking.calendar_sync_fail_open is
    False (the default) — signals available_slots to return no slots
    for the day rather than book against unconfirmed real availability.
    Never escapes available_slots itself."""


def _google_busy_intervals(db: Session, cfg: dict, date_str: str) -> list[tuple[int, int]]:
    """Busy ranges from the connected Google Calendar, or [] if sync
    isn't enabled/connected. Raises CalendarSyncUnavailableError if
    sync is enabled+connected but the Google API call failed and
    booking.calendar_sync_fail_open is False — the caller propagates
    that straight into "no slots today," the documented safety-over-
    convenience default (see PASS12_NOTES.md)."""
    if not get_setting(db, "features.calendar_sync_enabled"):
        return []
    from app import calendar_sync_service
    credential = calendar_sync_service.get_active_credential(db)
    if credential is None or not credential.calendar_id:
        return []
    try:
        return calendar_sync_service.busy_minutes_for_date(db, credential, date_str, timezone=cfg["timezone"])
    except Exception:
        if get_setting(db, "booking.calendar_sync_fail_open"):
            return []  # ignore the external calendar for this request, admin opted into this
        raise CalendarSyncUnavailableError(date_str)


def available_slots(
    db: Session, date_str: str, *, service_id: str | None = None, exclude_id: str | None = None
) -> list[str]:
    """Raises ValueError on a malformed date string, InvalidServiceError
    if service_id doesn't resolve to an active Service. Returns [] (not
    an error) for any date that's simply unbookable - closed day, past,
    too far ahead, or (Pass 12) an unreachable synced calendar with
    fail-open turned off - since "no slots" is the normal, safe outcome
    for all of these rather than a request error."""
    date = dt.date.fromisoformat(date_str)  # raises ValueError on bad format
    cfg = _booking_config(db)
    service = _resolve_service(db, service_id)  # raises InvalidServiceError
    now = _now(cfg)
    today = now.date()

    if date < today or date > today + dt.timedelta(days=cfg["max_days_ahead"]):
        return []

    ranges = _day_ranges(db, cfg, date, service_id)
    if not ranges:
        return []

    all_slots = _grid_slots_for_ranges(cfg, ranges)
    if not all_slots:
        return []

    try:
        google_busy = _google_busy_intervals(db, cfg, date_str)
    except CalendarSyncUnavailableError:
        return []

    duration, buf_before, buf_after = _duration_and_buffers(cfg, service)
    blocked = _booked_intervals(db, cfg, date_str, exclude_id=exclude_id) + google_busy
    earliest_bookable = now + dt.timedelta(hours=cfg["min_notice_hours"])

    out = []
    for s in all_slots:
        start_min = _time_to_minutes(s)
        end_min = start_min + duration
        if not _fits_in_ranges(start_min, end_min, ranges):
            continue  # wouldn't finish within an open range (e.g. runs past closing)

        cand_start, cand_end = start_min - buf_before, end_min + buf_after
        if any(cand_start < b_end and cand_end > b_start for b_start, b_end in blocked):
            continue

        slot_dt = dt.datetime.combine(date, dt.time.fromisoformat(s), tzinfo=ZoneInfo(cfg["timezone"]))
        if slot_dt < earliest_bookable:
            continue
        out.append(s)
    return out


_lock_seeded = False  # process-local memo — see _acquire_booking_lock


def _acquire_booking_lock(db: Session) -> None:
    """Serializes booking/reschedule requests against each other so that
    "check available_slots, then insert/move an appointment" behaves as
    one atomic step even under concurrent requests. Must be the very
    first thing the caller does with `db` — before any other read or
    write in that request — and the caller's transaction must not
    commit until after its own insert/update, since committing is what
    releases the lock.

    Implemented as a real write (UPDATE, not SELECT ... FOR UPDATE)
    against a single sentinel row (BookingLock id=1), because SQLite —
    used in dev and in this test suite — has no row-level locking and
    silently no-ops a bare FOR UPDATE, which would leave the race this
    exists to close wide open outside of MySQL/Postgres. An UPDATE
    takes a real, held-until-commit write lock identically on SQLite,
    MySQL, and Postgres, which is what actually forces a second
    concurrent caller to wait here until the first one commits or
    rolls back.

    The sentinel row is seeded lazily (first call in the process's
    lifetime, memoized in _lock_seeded so later calls skip straight to
    the UPDATE) rather than only in app.db.sync_schema, since a test DB
    built directly with Base.metadata.create_all never runs sync_schema
    at all. That seeding deliberately happens on connections of its own,
    fully opened and closed *before* `db` is touched at all — not just
    committed independently. On SQLite, even a read against `db` starts
    an implicit transaction that's held open (and holds a file-level
    lock) until the caller's eventual commit; starting that first and
    only then opening a second connection to seed the row would make
    the seed insert wait on a lock `db` itself is holding, and `db`
    isn't going anywhere until this function returns — a self-deadlock.
    Doing all the seed work first, on connections that are fully closed
    (rolled back or committed) before `db.execute` ever runs, avoids it.
    """
    global _lock_seeded
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    if not _lock_seeded:
        bind = db.get_bind()
        with bind.connect() as conn:
            row = conn.execute(text("SELECT 1 FROM booking_lock WHERE id = 1")).first()
        if row is None:
            try:
                with bind.connect() as conn, conn.begin():
                    conn.execute(text("INSERT INTO booking_lock (id, touched_at) VALUES (1, NULL)"))
            except IntegrityError:
                pass  # a concurrent caller won the seed race; the row exists now either way
        _lock_seeded = True
    db.execute(text("UPDATE booking_lock SET touched_at = :now WHERE id = 1"), {"now": now})


def _generate_code(db: Session) -> str:
    for _ in range(10):
        code = "PRN-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))
        if db.get(Appointment, code) is None:
            return code
    raise RuntimeError("Could not generate a unique appointment code")


def create_appointment(
    db: Session, *, date_str: str, time_str: str, name: str, email: str,
    phone: str = "", service: str = "", notes: str = "", lang: str = "en",
    service_id: str | None = None, answers: list[dict] | None = None,
) -> dict:
    if not name.strip():
        return {"ok": False, "error": "invalid_name"}
    if not EMAIL_RE.match(email):
        return {"ok": False, "error": "invalid_email"}
    # Must happen before available_slots() below — see
    # _acquire_booking_lock's docstring. Held until the router's
    # subsequent db.commit() persists (or a raised exception rolls
    # back) the appointment this call is about to create.
    _acquire_booking_lock(db)
    try:
        slots = available_slots(db, date_str, service_id=service_id)
    except ValueError:
        return {"ok": False, "error": "invalid_date"}
    except InvalidServiceError:
        return {"ok": False, "error": "invalid_service"}

    if time_str not in slots:
        return {"ok": False, "error": "slot_unavailable"}

    svc = db.get(Service, service_id) if service_id else None
    answer_map: dict[str, str] = {}
    if svc is not None:
        answer_map = {a.get("question_id"): (a.get("answer") or "").strip() for a in (answers or [])}
        known_ids = {q.id for q in svc.questions}
        if set(answer_map) - known_ids:
            return {"ok": False, "error": "invalid_question"}
        if any(q.required and not answer_map.get(q.id) for q in svc.questions):
            return {"ok": False, "error": "missing_required_answer"}

    appt = Appointment(
        id=_generate_code(db), date=date_str, time=time_str, lang=lang or "en",
        # Snapshotted at booking time (see Appointment.timezone's
        # docstring) - a separate read of booking.timezone from the one
        # inside available_slots() above, but get_setting is
        # process-cached (settings_service.py), so this costs nothing
        # extra in practice.
        timezone=_booking_config(db)["timezone"],
        name=name.strip(), email=email.strip(), phone=phone.strip(),
        service=service.strip(), service_id=service_id, notes=notes.strip(),
        status="pending" if (svc is not None and svc.requires_confirmation) else "confirmed",
    )
    db.add(appt)
    db.flush()

    if svc is not None:
        for q in svc.questions:
            ans = answer_map.get(q.id, "")
            if ans:
                db.add(AppointmentQuestionAnswer(
                    appointment_id=appt.id, question_id=q.id, question_label=q.label, answer=ans
                ))

    # A booking is a strong, unambiguous signal — always worth a lead
    # record, whether or not this person ever chatted first.
    from app import leads_service
    booked_what = svc.name if svc is not None else (appt.service or "general enquiry")
    leads_service.capture_lead(
        db, email=appt.email, source="booking", name=appt.name, phone=appt.phone,
        transcript_entry={"from": "system", "text": f"Booked {appt.date} {appt.time} ({booked_what})"},
    )
    return {"ok": True, "id": appt.id, "pending": appt.status == "pending", "appointment": _serialize(db, appt)}


def _find_by_id_and_email(db: Session, appt_id: str, email: str) -> Appointment | None:
    appt = db.get(Appointment, appt_id)
    if appt is None or appt.email.lower() != email.strip().lower():
        return None
    return appt


def lookup_appointment(db: Session, appt_id: str, email: str) -> dict:
    appt = _find_by_id_and_email(db, appt_id, email)
    if appt is None:
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "appointment": _serialize(db, appt)}


def _has_enough_notice(db: Session, appt: Appointment) -> bool:
    cfg = _booking_config(db)
    now = _now(cfg)
    # Prefer the timezone this appointment was actually booked/moved
    # under (see Appointment.timezone) over the live setting, so
    # changing booking.timezone later can't silently move an existing
    # appointment's notice-window deadline.
    tz = ZoneInfo(appt.timezone or cfg["timezone"])
    appt_dt = dt.datetime.combine(dt.date.fromisoformat(appt.date), dt.time.fromisoformat(appt.time), tzinfo=tz)
    # An appointment already in the past always allows cancellation
    # (nothing left to protect by refusing) — reschedules are guarded
    # separately, by the new slot's own notice window.
    if appt_dt <= now:
        return True
    return appt_dt - now >= dt.timedelta(hours=cfg["min_notice_hours"])


def cancel_appointment(db: Session, appt_id: str, email: str) -> dict:
    appt = _find_by_id_and_email(db, appt_id, email)
    if appt is None:
        return {"ok": False, "error": "not_found"}
    if appt.status == "cancelled":
        return {"ok": True, "appointment": _serialize(db, appt), "already_cancelled": True}  # idempotent
    if not _has_enough_notice(db, appt):
        return {"ok": False, "error": "notice_window_passed"}
    appt.status = "cancelled"
    return {"ok": True, "appointment": _serialize(db, appt), "already_cancelled": False}


def reschedule_appointment(db: Session, appt_id: str, email: str, new_date_str: str, new_time_str: str) -> dict:
    # Must happen before the availability re-check below — see
    # _acquire_booking_lock's docstring. Taken up front (even though
    # this call may still bail out on not_found/notice-window) rather
    # than only once we know we'll write, since the whole point is to
    # prevent another request's create/reschedule from slipping in
    # between this function's read of available_slots() and its own
    # write further down.
    _acquire_booking_lock(db)
    appt = _find_by_id_and_email(db, appt_id, email)
    if appt is None:
        return {"ok": False, "error": "not_found"}
    if appt.status == "cancelled":
        return {"ok": False, "error": "already_cancelled"}
    if not _has_enough_notice(db, appt):
        return {"ok": False, "error": "notice_window_passed"}

    try:
        # Reschedule keeps whatever service the booking was originally
        # made under (it isn't something the visitor picks again here)
        # — if that service was deactivated since, this fails cleanly
        # rather than silently re-slotting the appointment as generic.
        slots = available_slots(db, new_date_str, service_id=appt.service_id, exclude_id=appt.id)
    except ValueError:
        return {"ok": False, "error": "invalid_date"}
    except InvalidServiceError:
        return {"ok": False, "error": "invalid_service"}
    if new_time_str not in slots:
        return {"ok": False, "error": "slot_unavailable"}

    appt.date = new_date_str
    appt.time = new_time_str
    # Re-snapshot: the new date/time was just chosen from slots computed
    # under the *current* live booking.timezone (available_slots above),
    # so that's what this appointment's stored timezone should become
    # too — see Appointment.timezone's docstring.
    appt.timezone = _booking_config(db)["timezone"]
    return {"ok": True, "appointment": _serialize(db, appt)}


def admin_reschedule_appointment(db: Session, appt_id: str, new_date_str: str, new_time_str: str) -> dict:
    """Admin override of reschedule_appointment — no email match, no
    notice-window restriction (same reasoning as admin_cancel_appointment:
    an admin moving a booking is often exactly a late-notice change a
    visitor can no longer self-serve), but still respects the slot grid
    so it can't create a double-booking."""
    # See _acquire_booking_lock's docstring — same reasoning as
    # reschedule_appointment above.
    _acquire_booking_lock(db)
    appt = db.get(Appointment, appt_id)
    if appt is None:
        return {"ok": False, "error": "not_found"}
    if appt.status == "cancelled":
        return {"ok": False, "error": "already_cancelled"}
    try:
        slots = available_slots(db, new_date_str, service_id=appt.service_id, exclude_id=appt.id)
    except ValueError:
        return {"ok": False, "error": "invalid_date"}
    except InvalidServiceError:
        return {"ok": False, "error": "invalid_service"}
    if new_time_str not in slots:
        return {"ok": False, "error": "slot_unavailable"}

    appt.date = new_date_str
    appt.time = new_time_str
    appt.timezone = _booking_config(db)["timezone"]  # re-snapshot — same reasoning as reschedule_appointment above
    return {"ok": True, "appointment": _serialize(db, appt)}


def _serialize(db: Session, appt: Appointment) -> dict:
    service_name = None
    if appt.service_id:
        svc = db.get(Service, appt.service_id)
        service_name = svc.name if svc is not None else None
    answers = [
        {"question_id": a.question_id, "label": a.question_label, "answer": a.answer}
        for a in db.scalars(
            select(AppointmentQuestionAnswer).where(AppointmentQuestionAnswer.appointment_id == appt.id)
        )
    ]
    return {
        "id": appt.id, "date": appt.date, "time": appt.time, "slot": appt.time,
        "timezone": appt.timezone,  # the IANA zone date/time above should be read in — see Appointment.timezone
        "name": appt.name, "email": appt.email, "phone": appt.phone,
        "service": appt.service, "service_id": appt.service_id, "service_name": service_name,
        "notes": appt.notes, "status": appt.status,
        "confirmed_at": appt.confirmed_at.isoformat() if appt.confirmed_at else None,
        "external_event_id": appt.external_event_id,
        "calendar_drift": appt.calendar_drift,
        "answers": answers,
    }


# ── Admin-side listing ──────────────────────────────────────────────

def list_appointments(db: Session, *, date_from: str | None = None, date_to: str | None = None,
                       status: str | None = None) -> list[dict]:
    stmt = select(Appointment).order_by(Appointment.date, Appointment.time)
    if date_from:
        stmt = stmt.where(Appointment.date >= date_from)
    if date_to:
        stmt = stmt.where(Appointment.date <= date_to)
    if status:
        stmt = stmt.where(Appointment.status == status)
    return [_serialize(db, a) for a in db.scalars(stmt)]


def admin_cancel_appointment(db: Session, appt_id: str) -> dict:
    """Admin override - no notice-window restriction, since the whole
    point of an admin cancelling is often exactly a late-notice change
    the visitor themselves can no longer self-serve."""
    appt = db.get(Appointment, appt_id)
    if appt is None:
        return {"ok": False, "error": "not_found"}
    appt.status = "cancelled"
    return {"ok": True}


def admin_accept_appointment(db: Session, appt_id: str) -> dict:
    """Valid only from 'pending' — accepting an already-confirmed or
    cancelled appointment is a state-machine error, not something to
    silently allow or 500 on, so it comes back as a typed 'invalid_state'
    the router can turn into a 409."""
    appt = db.get(Appointment, appt_id)
    if appt is None:
        return {"ok": False, "error": "not_found"}
    if appt.status != "pending":
        return {"ok": False, "error": "invalid_state"}
    appt.status = "confirmed"
    appt.confirmed_at = dt.datetime.now(dt.timezone.utc)
    return {"ok": True, "appointment": _serialize(db, appt)}


def admin_reject_appointment(db: Session, appt_id: str, *, reason: str = "") -> dict:
    """Valid only from 'pending', same as accept. `reason` is folded
    into `notes` with a distinguishable "[declined]" prefix rather than
    a new column, consistent with keeping the schema lean — see
    PASS10_NOTES.md for why a dedicated column wasn't worth it here."""
    appt = db.get(Appointment, appt_id)
    if appt is None:
        return {"ok": False, "error": "not_found"}
    if appt.status != "pending":
        return {"ok": False, "error": "invalid_state"}
    appt.status = "cancelled"
    reason = (reason or "").strip()
    prefix = f"[declined] {reason}" if reason else "[declined]"
    appt.notes = f"{prefix}\n{appt.notes}" if appt.notes else prefix
    return {"ok": True, "appointment": _serialize(db, appt)}


def expire_stale_pending_appointments(db: Session) -> list[dict]:
    """Transitions every pending appointment older than
    booking.pending_expiry_hours to cancelled — an admin-side twin of
    admin_reject_appointment, just triggered by age instead of an
    admin click. _booked_intervals already stops treating an
    appointment this stale as blocking a slot; this is what makes the
    appointment's own status catch up to that, rather than it sitting
    forever showing "pending" while quietly no longer holding anything.

    Called from app/scheduler.py on a timer
    (booking.pending_expiry_poll_minutes), not from any HTTP route —
    there's no request to hang side effects (notification, webhook,
    calendar cleanup) off, so this only does the state transition and
    returns the newly-expired appointments (serialized) for the caller
    to run those side effects against, the same division of
    responsibility the routers already use for a normal cancel. A
    no-op, returning [], when booking.pending_expiry_hours is 0."""
    cfg = _booking_config(db)
    cutoff = _pending_cutoff(cfg)
    if cutoff is None:
        return []
    stmt = select(Appointment).where(Appointment.status == "pending")
    expired = []
    for appt in db.scalars(stmt):
        if _as_utc(appt.created_at) >= cutoff:
            continue
        appt.status = "cancelled"
        prefix = "[auto-declined] no response within the request window"
        appt.notes = f"{prefix}\n{appt.notes}" if appt.notes else prefix
        expired.append(_serialize(db, appt))
    return expired
