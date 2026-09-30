"""Regression test for the check-then-insert double-booking race closed
by booking_service._acquire_booking_lock: two visitors requesting the
exact same slot at the exact same instant must not both succeed."""
from __future__ import annotations

import datetime as dt
import threading

import pytest
from fastapi.testclient import TestClient

from app.db import session_scope
from app.main import app
from app.settings_service import set_setting


@pytest.fixture(autouse=True)
def _widen_booking_window():
    """This file's dates start at nth-workday 40 — clear of both the
    unwidened default window (30 calendar days) and of
    test_calendar_sync.py's window (nth-workday 250, comfortably far
    away). Bump the starting n here if a future test file also needs
    its own untouched booking window — but note booking.max_days_ahead
    is capped at 365 (settings_registry.py), which is only ~260
    *weekdays*, so there's limited room for many such windows; n=250
    already leaves test_calendar_sync.py little headroom below that
    cap, which is worth knowing before picking another big offset."""
    with session_scope() as db:
        set_setting(db, "booking.max_days_ahead", 90, actor_id=None, actor_username="test-setup")
    yield
    with session_scope() as db:
        set_setting(db, "booking.max_days_ahead", 30, actor_id=None, actor_username="test-teardown")


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


def test_double_booking_race_only_one_wins():
    date_str = _nth_future_workday(40)
    slot = "09:00"
    results: list[dict | None] = [None, None]
    start_barrier = threading.Barrier(2)

    def _book(i: int) -> None:
        c = TestClient(app)
        start_barrier.wait()  # both threads fire their POST as close together as possible
        resp = c.post("/api/booking/appointments", json={**VALID_APPT, "date": date_str, "slot": slot})
        results[i] = resp.json()

    threads = [threading.Thread(target=_book, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    oks = [r["ok"] for r in results]
    assert oks.count(True) == 1, f"expected exactly one booking to win the race, got {results}"
    loser = results[oks.index(False)]
    assert loser["error"] == "slot_unavailable"


def test_reschedule_race_against_new_booking_only_one_wins():
    """Same race, different entry points: one visitor is rescheduling an
    existing appointment into a slot at the same instant a second
    visitor is trying to book that slot fresh. _acquire_booking_lock is
    shared across create_appointment and reschedule_appointment
    precisely so this cross-endpoint race is closed too, not just the
    same-endpoint one above."""
    date_str = _nth_future_workday(41)
    target_slot = "10:00"
    origin_slot = "09:00"

    setup_client = TestClient(app)
    create_resp = setup_client.post(
        "/api/booking/appointments", json={**VALID_APPT, "date": date_str, "slot": origin_slot}
    )
    assert create_resp.status_code == 200, create_resp.text
    appt = create_resp.json()
    assert appt["ok"], appt

    results: list[dict | None] = [None, None]
    start_barrier = threading.Barrier(2)

    def _reschedule() -> None:
        c = TestClient(app)
        start_barrier.wait()
        resp = c.post(
            "/api/booking/appointments/reschedule",
            json={"id": appt["id"], "email": VALID_APPT["email"], "date": date_str, "time": target_slot},
        )
        results[0] = resp.json()

    def _fresh_book() -> None:
        c = TestClient(app)
        start_barrier.wait()
        resp = c.post(
            "/api/booking/appointments", json={**VALID_APPT, "date": date_str, "slot": target_slot}
        )
        results[1] = resp.json()

    threads = [threading.Thread(target=_reschedule), threading.Thread(target=_fresh_book)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    oks = [r["ok"] for r in results]
    assert oks.count(True) == 1, f"expected exactly one of reschedule/fresh-book to win, got {results}"
