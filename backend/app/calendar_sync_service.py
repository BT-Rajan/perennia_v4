"""
Google Calendar sync — connection lifecycle (OAuth), busy-time lookup
for slot generation, and best-effort event creation/cleanup on
booking confirm/cancel/reschedule. See docs/CALENDAR_MODULE_PLAN.md
(Pass 12).

One connected account for the whole business (not per-admin-user) —
`get_active_credential` is the only lookup every other module needs;
nothing here assumes multiple connections will ever exist at once.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import google_calendar_client as google
from app.models import AuditLog, CalendarCredential
from app.security import decrypt_secret, encrypt_secret
from app.settings_service import get_setting

# Refresh a bit before actual expiry so a slow request never straddles
# the token becoming invalid mid-call.
_REFRESH_SKEW = dt.timedelta(minutes=2)


class CalendarSyncNotConfigured(Exception):
    """Raised when calendar_sync.google_client_id/secret aren't set —
    distinct from GoogleCalendarError (a real API failure) since this
    is an admin setup gap, not something retrying would fix."""


def _oauth_client(db: Session) -> tuple[str, str]:
    client_id = get_setting(db, "calendar_sync.google_client_id")
    client_secret = get_setting(db, "calendar_sync.google_client_secret")
    if not client_id or not client_secret:
        raise CalendarSyncNotConfigured(
            "calendar_sync.google_client_id / google_client_secret must be set before connecting"
        )
    return client_id, client_secret


def get_active_credential(db: Session) -> CalendarCredential | None:
    return db.scalar(select(CalendarCredential).where(CalendarCredential.is_active.is_(True)))


def build_connect_url(db: Session, *, redirect_uri: str, admin_id: str) -> str:
    from app.security import sign_oauth_state
    client_id, _ = _oauth_client(db)
    return google.build_auth_url(client_id=client_id, redirect_uri=redirect_uri, state=sign_oauth_state(admin_id))


def complete_oauth_callback(db: Session, *, redirect_uri: str, code: str) -> tuple[CalendarCredential, list[dict]]:
    """Exchanges the code and stores the tokens — calendar not yet
    chosen, not yet active — and returns the account's calendar list so
    the caller can present a choice.

    Deliberately does NOT touch any existing active credential here.
    That used to happen at this point ("deactivate the old one, then
    the new one becomes active once a calendar is picked"), which
    opened a real gap: from the moment this runs until the admin
    finishes picking a calendar in select_calendar below, there was no
    active credential at all — every calendar-dependent thing
    (busy-time checks, event create/update/delete, drift detection)
    silently went dark, even though the previous connection was working
    fine right up until this request. If the admin got interrupted
    before finishing (closed the tab, got distracted), that gap was
    permanent, not brief. select_calendar deactivates the old
    credential and activates the new one together, in the same
    transaction, so there's never a moment with zero active
    credentials — the old connection keeps working right up until the
    new one is actually confirmed."""
    client_id, client_secret = _oauth_client(db)
    token_data = google.exchange_code(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, code=code)

    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        # Google only issues one on first consent for this account+app;
        # without it we can't stay connected past the access token's
        # ~1 hour lifetime, so this must surface as an error, not a
        # credential that silently stops working later.
        raise google.GoogleCalendarError(
            "Google did not return a refresh_token — the account may have already granted access once "
            "before; revoke access at https://myaccount.google.com/permissions and reconnect."
        )

    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=token_data.get("expires_in", 3600))

    credential = CalendarCredential(
        provider="google",
        access_token=encrypt_secret(token_data["access_token"]),
        refresh_token=encrypt_secret(refresh_token),
        token_expires_at=expires_at,
        calendar_id=None, is_active=False,
    )
    db.add(credential)
    db.add(AuditLog(action="calendar_sync.connect"))
    db.flush()

    calendars = google.list_calendars(token_data["access_token"])
    return credential, calendars


def select_calendar(db: Session, credential_id: str, *, calendar_id: str,
                     actor_id: str | None, actor_username: str | None) -> CalendarCredential:
    """Activates `credential_id` with the chosen calendar. Any other
    active credential is deactivated in this same call — not earlier,
    in complete_oauth_callback — so the old connection stays fully
    working for as long as the admin takes to get here, and switching
    connections is atomic: never a moment with zero active credentials,
    only ever a direct handoff from the old one to the new one. See
    complete_oauth_callback's docstring for the outage this replaced."""
    credential = db.get(CalendarCredential, credential_id)
    if credential is None:
        raise KeyError(f"No calendar credential {credential_id!r}")
    for existing in db.scalars(select(CalendarCredential).where(
        CalendarCredential.is_active.is_(True), CalendarCredential.id != credential.id
    )):
        existing.is_active = False
    credential.calendar_id = calendar_id
    credential.is_active = True
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username,
                     action="calendar_sync.select_calendar", target=credential_id, detail=calendar_id))
    return credential


def disconnect(db: Session, *, actor_id: str | None, actor_username: str | None) -> bool:
    """Deletes the credential locally regardless of whether Google's
    own revoke call succeeds — an admin must never be stuck with a
    connection they can't remove just because the revoke request
    itself failed (network blip, token already invalid, etc)."""
    credential = get_active_credential(db)
    if credential is None:
        return False
    try:
        google.revoke_token(decrypt_secret(credential.refresh_token))
    except Exception:
        pass  # best-effort; local disconnect proceeds regardless
    db.delete(credential)
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username, action="calendar_sync.disconnect"))
    return True


def _ensure_fresh_access_token(db: Session, credential: CalendarCredential) -> str:
    """Returns a valid access token, refreshing and persisting it first
    if the stored one is expired or about to be."""
    # SQLite doesn't actually persist tzinfo on a DateTime(timezone=True)
    # column - reads back naive - so normalize before comparing, same
    # as app/deps.py's session-expiry check.
    expires_at = credential.token_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
    if expires_at - _REFRESH_SKEW > dt.datetime.now(dt.timezone.utc):
        return decrypt_secret(credential.access_token)

    client_id, client_secret = _oauth_client(db)
    token_data = google.refresh_access_token(
        client_id=client_id, client_secret=client_secret, refresh_token=decrypt_secret(credential.refresh_token)
    )
    credential.access_token = encrypt_secret(token_data["access_token"])
    credential.token_expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=token_data.get("expires_in", 3600))
    db.flush()
    return token_data["access_token"]


def busy_minutes_for_date(db: Session, credential: CalendarCredential, date_str: str, *, timezone: str) -> list[tuple[int, int]]:
    """One Free/Busy API call for the whole day (not once per candidate
    slot), returned as (start_minutes, end_minutes) pairs relative to
    midnight local time — the same shape booking_service.py already
    uses for every other blocked-interval source, so it can be merged
    into the same overlap check with zero special-casing. Raises
    GoogleCalendarError on any failure; the caller decides fail-open vs
    fail-closed (booking.calendar_sync_fail_open)."""
    from zoneinfo import ZoneInfo

    access_token = _ensure_fresh_access_token(db, credential)
    date = dt.date.fromisoformat(date_str)
    tz = ZoneInfo(timezone)
    day_start = dt.datetime.combine(date, dt.time.min, tzinfo=tz)
    day_end = day_start + dt.timedelta(days=1)

    busy = google.get_busy_times(access_token, calendar_id=credential.calendar_id, time_min=day_start, time_max=day_end)

    ranges = []
    for start_iso, end_iso in busy:
        start_local = dt.datetime.fromisoformat(start_iso).astimezone(tz)
        end_local = dt.datetime.fromisoformat(end_iso).astimezone(tz)
        start_min = max(0, int((start_local - day_start).total_seconds() // 60))
        end_min = min(24 * 60, int((end_local - day_start).total_seconds() // 60))
        if end_min > start_min:
            ranges.append((start_min, end_min))
    return ranges


# ── Event creation on confirm (best-effort, mirrors notification_service.py) ──

def create_event_for_appointment(db: Session, appt_id: str) -> str | None:
    """Best-effort: creates a Google Calendar event for this
    appointment and persists its id onto Appointment.external_event_id
    if successful, returning that id so a caller holding an
    already-serialized copy of the appointment (as every router here
    does — the dict returned by booking_service.create_appointment is
    built *before* this runs) can patch it in rather than silently
    returning stale data. Never raises — an appointment is already
    confirmed by the time this runs, and a calendar-sync hiccup must
    never turn that into a broken booking response, matching
    notification_service.py's philosophy exactly."""
    if not get_setting(db, "features.calendar_sync_enabled"):
        return None
    credential = get_active_credential(db)
    if credential is None or not credential.calendar_id:
        return None
    from app.models import Appointment
    appt = db.get(Appointment, appt_id)
    if appt is None:
        return None
    try:
        access_token = _ensure_fresh_access_token(db, credential)
        # Prefer the timezone this appointment was actually booked under
        # (see Appointment.timezone's docstring) over the live setting,
        # so a later booking.timezone change can't retroactively shift
        # where this event lands on Google.
        timezone = appt.timezone or get_setting(db, "booking.timezone")
        from zoneinfo import ZoneInfo
        start_local = dt.datetime.fromisoformat(f"{appt.date}T{appt.time}:00").replace(tzinfo=ZoneInfo(timezone))
        duration = _appointment_duration_minutes(db, appt)
        end_local = start_local + dt.timedelta(minutes=duration)
        event_id = google.create_event(
            access_token, calendar_id=credential.calendar_id,
            summary=f"{appt.service or 'Appointment'} — {appt.name}",
            description=appt.notes or "", start_iso=start_local.isoformat(), end_iso=end_local.isoformat(),
            timezone=timezone,
        )
        appt.external_event_id = event_id
        db.flush()
        return event_id
    except Exception:
        import logging
        logging.getLogger("perennia.calendar_sync").exception(
            "Google Calendar event creation failed for appointment %s", appt_id
        )
        return None


def update_event_for_appointment(db: Session, appt_id: str) -> str | None:
    """Best-effort. If this appointment already has a linked Google
    event, PATCHes it in place (new date/time/description) instead of
    the old delete-then-recreate — preserves the event's Google id and
    anything attached to it there. If there's no linked event yet (sync
    turned on after this appointment was first confirmed, or the
    original create silently failed), falls back to creating one.

    If the PATCH fails specifically because the linked event is gone on
    Google's side (a 404), falls back to recreating it rather than
    leaving the appointment silently unsynced. Any *other* failure — a
    timeout, a 429, a 500 — does NOT fall back to recreating: the
    original event is presumably still sitting on the calendar
    untouched, and unconditionally recreating on every failure used to
    leave it there, orphaned, while a duplicate got created alongside
    it. Those failures are logged and left for a retry or the next
    drift check to resolve instead of being made worse. Never raises —
    same philosophy as create_event_for_appointment."""
    if not get_setting(db, "features.calendar_sync_enabled"):
        return None
    credential = get_active_credential(db)
    if credential is None or not credential.calendar_id:
        return None
    from app.models import Appointment
    appt = db.get(Appointment, appt_id)
    if appt is None:
        return None
    if not appt.external_event_id:
        return create_event_for_appointment(db, appt_id)
    try:
        access_token = _ensure_fresh_access_token(db, credential)
        # Same reasoning as create_event_for_appointment above.
        timezone = appt.timezone or get_setting(db, "booking.timezone")
        from zoneinfo import ZoneInfo
        start_local = dt.datetime.fromisoformat(f"{appt.date}T{appt.time}:00").replace(tzinfo=ZoneInfo(timezone))
        duration = _appointment_duration_minutes(db, appt)
        end_local = start_local + dt.timedelta(minutes=duration)
        google.update_event(
            access_token, calendar_id=credential.calendar_id, event_id=appt.external_event_id,
            summary=f"{appt.service or 'Appointment'} — {appt.name}",
            description=appt.notes or "", start_iso=start_local.isoformat(), end_iso=end_local.isoformat(),
            timezone=timezone,
        )
        appt.calendar_drift = None  # this push supersedes any previously-flagged mismatch
        db.flush()
        return appt.external_event_id
    except google.GoogleCalendarError as e:
        import logging
        logger = logging.getLogger("perennia.calendar_sync")
        if e.status_code == 404:
            logger.exception(
                "Google Calendar event %s for appointment %s is gone (404) — recreating it",
                appt.external_event_id, appt_id,
            )
            try:
                return create_event_for_appointment(db, appt_id)
            except Exception:
                return None
        logger.exception(
            "Google Calendar event update failed for appointment %s (status=%s) — leaving the existing "
            "event as-is rather than risking a duplicate; will be retried on the next drift check",
            appt_id, e.status_code,
        )
        return None
    except Exception:
        # Not even a GoogleCalendarError — e.g. _ensure_fresh_access_token's
        # own failure modes (decrypt error, refresh failure). Same
        # reasoning as the branch above: don't recreate, just report.
        import logging
        logging.getLogger("perennia.calendar_sync").exception(
            "Google Calendar event update failed unexpectedly for appointment %s", appt_id
        )
        return None


def delete_event_for_appointment(db: Session, appt_id: str) -> None:
    """Best-effort cleanup on cancel/reschedule — never raises. Clears
    external_event_id on success so a later call is a no-op rather
    than repeatedly attempting to delete an event that's already
    gone."""
    from app.models import Appointment
    appt = db.get(Appointment, appt_id)
    if appt is None or not appt.external_event_id:
        return
    credential = get_active_credential(db)
    if credential is None or not credential.calendar_id:
        return
    try:
        access_token = _ensure_fresh_access_token(db, credential)
        google.delete_event(access_token, calendar_id=credential.calendar_id, event_id=appt.external_event_id)
        appt.external_event_id = None
        db.flush()
    except Exception:
        import logging
        logging.getLogger("perennia.calendar_sync").exception(
            "Google Calendar event deletion failed for appointment %s", appt_id
        )


def _appointment_duration_minutes(db: Session, appt) -> int:
    from app.models import Service
    if appt.service_id:
        svc = db.get(Service, appt.service_id)
        if svc is not None:
            return svc.duration_minutes
    return get_setting(db, "booking.slot_minutes")


# ── Manual event management (admin's general "Calendar" screen) ─────
# Everything above this point is triggered by an Appointment row and
# never exposes raw Google event shapes to a caller. These functions
# are the opposite: an admin managing the connected calendar directly,
# for events that may have nothing to do with a booking at all. They
# operate on whatever calendar is currently connected/selected —
# exactly the "full calendar controls" a personal Google account needs
# for anyone to create/edit/delete arbitrary events from this app.

def _require_active_calendar(db: Session) -> CalendarCredential:
    credential = get_active_credential(db)
    if credential is None or not credential.calendar_id:
        raise CalendarSyncNotConfigured("No calendar is connected — connect one in Settings first")
    return credential


def _format_event(event: dict) -> dict:
    start = event.get("start", {})
    end = event.get("end", {})
    return {
        "id": event.get("id"),
        "summary": event.get("summary") or "(no title)",
        "description": event.get("description") or "",
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
        "all_day": "date" in start and "dateTime" not in start,
        "html_link": event.get("htmlLink"),
    }


def list_manual_events(db: Session, *, time_min: dt.datetime, time_max: dt.datetime) -> list[dict]:
    """Every (non-cancelled) event on the connected calendar within the
    window, regardless of whether this app created it — an admin needs
    to see the whole calendar to manage it, not just the appointments
    this app happens to know about."""
    credential = _require_active_calendar(db)
    access_token = _ensure_fresh_access_token(db, credential)
    items, _ = google.list_all_events(
        access_token, calendar_id=credential.calendar_id,
        time_min=time_min.isoformat(), time_max=time_max.isoformat(),
    )
    return [_format_event(e) for e in items if e.get("status") != "cancelled"]


def create_manual_event(db: Session, *, summary: str, description: str, start_iso: str, end_iso: str,
                         timezone: str, actor_id: str | None, actor_username: str | None) -> dict:
    credential = _require_active_calendar(db)
    access_token = _ensure_fresh_access_token(db, credential)
    event_id = google.create_event(
        access_token, calendar_id=credential.calendar_id, summary=summary,
        description=description, start_iso=start_iso, end_iso=end_iso, timezone=timezone,
    )
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username,
                     action="calendar_sync.create_event", target=event_id))
    return {"id": event_id}


def update_manual_event(db: Session, event_id: str, *, summary: str, description: str, start_iso: str,
                         end_iso: str, timezone: str, actor_id: str | None, actor_username: str | None) -> None:
    credential = _require_active_calendar(db)
    access_token = _ensure_fresh_access_token(db, credential)
    google.update_event(
        access_token, calendar_id=credential.calendar_id, event_id=event_id,
        summary=summary, description=description, start_iso=start_iso, end_iso=end_iso, timezone=timezone,
    )
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username,
                     action="calendar_sync.update_event", target=event_id))
    _clear_drift_for_event(db, event_id)


def delete_manual_event(db: Session, event_id: str, *, actor_id: str | None, actor_username: str | None) -> None:
    credential = _require_active_calendar(db)
    access_token = _ensure_fresh_access_token(db, credential)
    google.delete_event(access_token, calendar_id=credential.calendar_id, event_id=event_id)
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username,
                     action="calendar_sync.delete_event", target=event_id))
    appt = _appointment_for_event(db, event_id)
    if appt is not None:
        appt.calendar_drift = "Linked calendar event was deleted from the admin Calendar screen."


def _appointment_for_event(db: Session, event_id: str):
    from app.models import Appointment
    return db.scalar(select(Appointment).where(Appointment.external_event_id == event_id))


def _clear_drift_for_event(db: Session, event_id: str) -> None:
    appt = _appointment_for_event(db, event_id)
    if appt is not None:
        appt.calendar_drift = None


# ── Two-way drift detection ───────────────────────────────────────────

def detect_drift(db: Session) -> dict:
    """Reconciles appointments against what's actually on the connected
    Google Calendar right now — catches an event someone edited or
    deleted directly in Google rather than through this app, which the
    one-directional create/update/delete calls above would otherwise
    never notice. Uses Google's incremental sync (a stored syncToken)
    so a routine check is one cheap request instead of re-listing the
    whole calendar; falls back to a full time-bounded listing the first
    time, or whenever Google reports the stored token stale (410).

    Never raises — reports failure in the returned dict instead, so an
    admin-triggered 'Sync now' always gets a clean response and a
    scheduled background run never crashes its caller."""
    credential = get_active_credential(db)
    if credential is None or not credential.calendar_id:
        return {"ok": False, "error": "not_connected", "checked": 0, "flagged": 0}

    from app.models import Appointment
    try:
        access_token = _ensure_fresh_access_token(db, credential)
        default_timezone = get_setting(db, "booking.timezone")

        try:
            if not credential.sync_token:
                raise google.SyncTokenExpired("no sync token yet — first run")
            items, next_token = google.list_all_events(
                access_token, calendar_id=credential.calendar_id, sync_token=credential.sync_token,
            )
        except google.SyncTokenExpired:
            credential.sync_token = None
            window_start = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
            window_end = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=365)
            items, next_token = google.list_all_events(
                access_token, calendar_id=credential.calendar_id,
                time_min=window_start.isoformat(), time_max=window_end.isoformat(),
            )

        flagged = 0
        for event in items:
            event_id = event.get("id")
            if not event_id:
                continue
            appt = db.scalar(select(Appointment).where(Appointment.external_event_id == event_id))
            if appt is None:
                continue  # not something this app created/linked - nothing of ours to reconcile

            if event.get("status") == "cancelled":
                appt.calendar_drift = "Deleted on Google Calendar — appointment record no longer matches."
                flagged += 1
                continue

            start = event.get("start", {}).get("dateTime")
            if not start:
                continue  # unexpected all-day shape for a booking event; skip rather than misreport
            # Prefer the timezone this specific appointment was actually
            # booked/moved under (see Appointment.timezone's docstring)
            # over the live setting — computed per-appointment, not once
            # for the whole batch, since different appointments here may
            # have been booked under different zones if the setting
            # changed in between. Without this, changing booking.timezone
            # would make every existing appointment look drifted (or
            # mask real drift) the very next time this runs.
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(appt.timezone or default_timezone)
            event_local = dt.datetime.fromisoformat(start).astimezone(tz)
            expected_local = dt.datetime.fromisoformat(f"{appt.date}T{appt.time}:00").replace(tzinfo=tz)
            if event_local != expected_local:
                appt.calendar_drift = (
                    f"Time changed on Google Calendar to {event_local.strftime('%Y-%m-%d %H:%M')} "
                    f"— appointment record still shows {appt.date} {appt.time}."
                )
                flagged += 1
            elif appt.calendar_drift:
                appt.calendar_drift = None  # back in sync

        credential.sync_token = next_token
        credential.last_synced_at = dt.datetime.now(dt.timezone.utc)
        db.flush()
        return {"ok": True, "checked": len(items), "flagged": flagged}
    except Exception:
        import logging
        logging.getLogger("perennia.calendar_sync").exception("Calendar drift detection failed")
        return {"ok": False, "error": "sync_failed", "checked": 0, "flagged": 0}
