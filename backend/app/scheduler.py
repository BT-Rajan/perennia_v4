"""
Two in-process background jobs:

1. calendar_drift_poll — periodically check the connected Google
   Calendar for events that changed outside this app (edited or
   deleted directly in Google) and flag any linked appointment that no
   longer matches. See calendar_sync_service.detect_drift.
2. pending_expiry_poll — periodically auto-decline pending appointments
   that have sat past booking.pending_expiry_hours with no admin
   action, so one doesn't hold its slot forever. See
   booking_service.expire_stale_pending_appointments.

Originally this was "a single in-process job... if a second recurring
job is ever needed, that's the point to reconsider [a dedicated worker
process]" — pending-expiry is that second job. Two is still small
enough that plain APScheduler in the same process remains the
pragmatic choice; a third would be the point to revisit that.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger("perennia.calendar_sync")

_scheduler: BackgroundScheduler | None = None
_DRIFT_JOB_ID = "calendar_drift_poll"
_PENDING_EXPIRY_JOB_ID = "pending_expiry_poll"


def _run_drift_check() -> None:
    from app.db import session_scope
    from app import calendar_sync_service
    from app.settings_service import get_setting

    with session_scope() as db:
        if not get_setting(db, "features.calendar_sync_enabled"):
            return
        if calendar_sync_service.get_active_credential(db) is None:
            return
        result = calendar_sync_service.detect_drift(db)
        if not result.get("ok"):
            logger.warning("Scheduled calendar drift check failed: %s", result.get("error"))
        elif result.get("flagged"):
            logger.info("Scheduled calendar drift check flagged %d appointment(s)", result["flagged"])


def _run_pending_expiry_check() -> None:
    from app.db import session_scope
    from app import booking_service, calendar_sync_service, notification_service, webhook_service

    with session_scope() as db:
        expired = booking_service.expire_stale_pending_appointments(db)
        # Committed here, ahead of the side effects below, the same
        # ordering the HTTP routers use (see public_booking.py) —
        # session_scope() only commits once, on the way out, and would
        # roll back these status changes too if a notification/webhook
        # call below raised, which must never undo an expiry that
        # already happened.
        db.commit()
        for appt in expired:
            try:
                # Same notification/event as an admin manually declining
                # a pending request (routers/admin_booking.py) — this is
                # exactly that, just triggered by age instead of a click.
                notification_service.notify_booking_declined(
                    db, appt, reason="No response within the request window"
                )
                webhook_service.dispatch_event(db, "booking.declined", appt)
                calendar_sync_service.delete_event_for_appointment(db, appt["id"])
            except Exception:
                # One appointment's side effects failing shouldn't stop
                # the rest of this batch from being processed — unlike
                # an HTTP request, which only ever handles one.
                logger.exception("Pending-expiry side effects failed for appointment %s", appt["id"])
        if expired:
            logger.info("Pending-expiry check auto-declined %d appointment(s)", len(expired))


def _add_job(fn, job_id: str, minutes: int) -> None:
    if minutes and minutes > 0:
        _scheduler.add_job(fn, "interval", minutes=minutes, id=job_id, max_instances=1, coalesce=True)


def start() -> None:
    """Called once from main.py's startup hook. Reads both poll
    intervals fresh from settings each time, not just at startup, so an
    admin changing either takes effect on that job's next tick without a
    restart — reschedule()/reschedule_pending_expiry() below handle an
    interval change made mid-run."""
    global _scheduler
    if _scheduler is not None:
        return
    from app.db import session_scope
    from app.settings_service import get_setting

    try:
        with session_scope() as db:
            drift_minutes = get_setting(db, "calendar_sync.drift_poll_minutes")
            expiry_minutes = get_setting(db, "booking.pending_expiry_poll_minutes")
    except Exception:
        # Settings table may not exist yet (fresh install before
        # init_db.py has run) - skip scheduling rather than crash startup.
        logger.exception("Could not read scheduler intervals at startup; background polling disabled")
        return

    _scheduler = BackgroundScheduler(daemon=True)
    _add_job(_run_drift_check, _DRIFT_JOB_ID, drift_minutes)
    _add_job(_run_pending_expiry_check, _PENDING_EXPIRY_JOB_ID, expiry_minutes)
    _scheduler.start()


def reschedule(minutes: int) -> None:
    """Call after an admin updates calendar_sync.drift_poll_minutes so
    the running scheduler picks up the new interval immediately."""
    if _scheduler is None:
        return
    if _scheduler.get_job(_DRIFT_JOB_ID) is not None:
        _scheduler.remove_job(_DRIFT_JOB_ID)
    _add_job(_run_drift_check, _DRIFT_JOB_ID, minutes)


def reschedule_pending_expiry(minutes: int) -> None:
    """Twin of reschedule() above, for booking.pending_expiry_poll_minutes."""
    if _scheduler is None:
        return
    if _scheduler.get_job(_PENDING_EXPIRY_JOB_ID) is not None:
        _scheduler.remove_job(_PENDING_EXPIRY_JOB_ID)
    _add_job(_run_pending_expiry_check, _PENDING_EXPIRY_JOB_ID, minutes)


def stop() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
