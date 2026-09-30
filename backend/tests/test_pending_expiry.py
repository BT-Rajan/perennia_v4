"""Regression tests for the pending-appointment TTL: a pending
appointment older than booking.pending_expiry_hours stops holding its
slot (_booked_intervals), and expire_stale_pending_appointments
actually resolves its status to match instead of it sitting forever as
"pending" while quietly no longer blocking anything."""
from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from app import booking_service
from app.db import session_scope
from app.main import app
from app.models import Appointment, Service
from app.settings_service import set_setting


@pytest.fixture(autouse=True)
def _widen_booking_window():
    """This file's dates start at nth-workday 60 — clear of
    test_booking_concurrency.py (40/41) and test_calendar_sync.py
    (160-169, 250-259)."""
    with session_scope() as db:
        set_setting(db, "booking.max_days_ahead", 90, actor_id=None, actor_username="test-setup")
    yield
    with session_scope() as db:
        set_setting(db, "booking.max_days_ahead", 30, actor_id=None, actor_username="test-teardown")


@pytest.fixture(autouse=True)
def _reset_pending_expiry_setting():
    yield
    with session_scope() as db:
        set_setting(db, "booking.pending_expiry_hours", 48, actor_id=None, actor_username="test-teardown")


def _nth_future_workday(n: int) -> str:
    d = dt.date.today()
    found = 0
    while True:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            found += 1
            if found == n:
                return d.isoformat()


VALID_APPT = {"name": "Jamie Rivera", "email": "jamie@example.com", "phone": "555-0100"}


def _make_confirmation_required_service() -> str:
    with session_scope() as db:
        svc = Service(
            name="Consultation", slug=f"consultation-{dt.datetime.now().timestamp()}",
            duration_minutes=30, requires_confirmation=True,
        )
        db.add(svc)
        db.flush()
        return svc.id


def test_stale_pending_stops_blocking_the_slot():
    with session_scope() as db:
        set_setting(db, "booking.pending_expiry_hours", 1, actor_id=None, actor_username="test-setup")

    service_id = _make_confirmation_required_service()
    date = _nth_future_workday(60)
    c = TestClient(app)

    created = c.post("/api/booking/appointments", json={
        **VALID_APPT, "date": date, "slot": "09:00", "service_id": service_id,
    }).json()
    assert created["ok"] is True, created
    assert created["pending"] is True

    # Still fresh — blocks the slot exactly like before this fix.
    slots = c.get(f"/api/booking/slots?date={date}&service_id={service_id}").json()
    assert "09:00" not in slots["slots"]

    # Backdate it past the 1-hour expiry window.
    with session_scope() as db:
        appt = db.get(Appointment, created["id"])
        appt.created_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)

    slots = c.get(f"/api/booking/slots?date={date}&service_id={service_id}").json()
    assert "09:00" in slots["slots"]


def test_expire_stale_pending_appointments_declines_it():
    with session_scope() as db:
        set_setting(db, "booking.pending_expiry_hours", 1, actor_id=None, actor_username="test-setup")

    service_id = _make_confirmation_required_service()
    date = _nth_future_workday(61)
    c = TestClient(app)

    created = c.post("/api/booking/appointments", json={
        **VALID_APPT, "date": date, "slot": "09:00", "service_id": service_id,
    }).json()

    with session_scope() as db:
        appt = db.get(Appointment, created["id"])
        appt.created_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)

    with session_scope() as db:
        expired = booking_service.expire_stale_pending_appointments(db)

    # A subset check, not exact-list equality: this sweep is global and
    # an earlier test in this file may have left its own stale pending
    # appointment sitting around too (same accepted cross-test-leakage
    # pattern test_calendar_sync.py documents) — this test only needs
    # to know its own appointment got swept up.
    expired_by_id = {a["id"]: a for a in expired}
    assert created["id"] in expired_by_id
    assert expired_by_id[created["id"]]["status"] == "cancelled"
    assert "auto-declined" in expired_by_id[created["id"]]["notes"]

    lookup = c.post("/api/booking/appointments/lookup", json={
        "id": created["id"], "email": VALID_APPT["email"],
    }).json()
    assert lookup["appointment"]["status"] == "cancelled"

    # Idempotent — a second sweep finds nothing left to expire.
    with session_scope() as db:
        assert booking_service.expire_stale_pending_appointments(db) == []


def test_pending_expiry_disabled_by_zero_never_expires():
    with session_scope() as db:
        set_setting(db, "booking.pending_expiry_hours", 0, actor_id=None, actor_username="test-setup")

    service_id = _make_confirmation_required_service()
    date = _nth_future_workday(62)
    c = TestClient(app)

    created = c.post("/api/booking/appointments", json={
        **VALID_APPT, "date": date, "slot": "09:00", "service_id": service_id,
    }).json()

    with session_scope() as db:
        appt = db.get(Appointment, created["id"])
        appt.created_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=365)

    # Disabled (0) means indefinite, exactly as it always behaved before this setting existed.
    slots = c.get(f"/api/booking/slots?date={date}&service_id={service_id}").json()
    assert "09:00" not in slots["slots"]

    with session_scope() as db:
        assert booking_service.expire_stale_pending_appointments(db) == []
