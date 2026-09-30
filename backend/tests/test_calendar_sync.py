"""Pass 12 — external calendar sync (Google, opt-in). No live Google
account is used or required: every test monkeypatches
app.google_calendar_client's functions directly, matching the plan's
"integration test against a mocked Google client" requirement.
See docs/CALENDAR_MODULE_PLAN.md and PASS12_NOTES.md."""
import datetime as dt

import pytest

from app.db import session_scope
from app.models import CalendarCredential
from app.security import encrypt_secret
from app.settings_service import set_setting


@pytest.fixture(autouse=True)
def _widen_booking_window():
    """This file's dates start at nth-workday 250, clear of every other
    file's window (see PASS9_NOTES.md)."""
    with session_scope() as db:
        set_setting(db, "booking.max_days_ahead", 365, actor_id=None, actor_username="test-setup")
    yield
    with session_scope() as db:
        set_setting(db, "booking.max_days_ahead", 30, actor_id=None, actor_username="test-teardown")


@pytest.fixture(autouse=True)
def _clear_calendar_state_after_test():
    """Every real booking made anywhere in the suite would otherwise
    try to sync against a credential left behind by this file — same
    pollution class documented in PASS9_NOTES.md/PASS11_NOTES.md."""
    yield
    with session_scope() as db:
        db.query(CalendarCredential).delete()
        set_setting(db, "features.calendar_sync_enabled", False, actor_id=None, actor_username="test-teardown")
        set_setting(db, "booking.calendar_sync_fail_open", False, actor_id=None, actor_username="test-teardown")


def _nth_future_workday(n: int) -> str:
    d = dt.date.today()
    found = 0
    while True:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            found += 1
            if found == n:
                return d.isoformat()


def _enable_sync(logged_in_client=None):
    with session_scope() as db:
        set_setting(db, "features.calendar_sync_enabled", True, actor_id=None, actor_username="test-setup")


def _create_active_credential(calendar_id="primary@group.calendar.google.com", expires_in_future=True):
    with session_scope() as db:
        cred = CalendarCredential(
            provider="google",
            access_token=encrypt_secret("fake-access-token"),
            refresh_token=encrypt_secret("fake-refresh-token"),
            token_expires_at=dt.datetime.now(dt.timezone.utc) + (
                dt.timedelta(hours=1) if expires_in_future else -dt.timedelta(hours=1)
            ),
            calendar_id=calendar_id, is_active=True,
        )
        db.add(cred)
        db.flush()
        return cred.id


def _configure_oauth_client(logged_in_client, redirect_uri="https://example.com/admin/api/calendar-sync/callback"):
    resp = logged_in_client.put("/admin/api/settings/calendar_sync", json={
        "calendar_sync.google_client_id": "test-client-id",
        "calendar_sync.google_client_secret": "test-client-secret",
        "calendar_sync.google_redirect_uri": redirect_uri,
    })
    assert resp.status_code == 200, resp.text


VALID_APPT = {"name": "Jamie Rivera", "email": "jamie@example.com", "phone": "555-0100"}


# ── OAuth connect flow ───────────────────────────────────────────────

def test_connect_requires_client_credentials_configured(logged_in_client):
    resp = logged_in_client.get("/admin/api/calendar-sync/connect", follow_redirects=False)
    assert resp.status_code == 400


def test_connect_redirects_to_google(logged_in_client):
    _configure_oauth_client(logged_in_client)
    resp = logged_in_client.get("/admin/api/calendar-sync/connect", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "state=" in resp.headers["location"]


def test_callback_invalid_state_rejected(logged_in_client):
    _configure_oauth_client(logged_in_client)
    resp = logged_in_client.get("/admin/api/calendar-sync/callback?code=abc&state=not-a-real-state")
    assert resp.status_code == 400


def test_full_connect_flow(logged_in_client, monkeypatch):
    _configure_oauth_client(logged_in_client)

    monkeypatch.setattr(
        "app.google_calendar_client.exchange_code",
        lambda **kw: {"access_token": "at-123", "refresh_token": "rt-456", "expires_in": 3600},
    )
    monkeypatch.setattr(
        "app.google_calendar_client.list_calendars",
        lambda access_token: [{"id": "primary", "summary": "Primary", "primary": True}],
    )

    connect = logged_in_client.get("/admin/api/calendar-sync/connect", follow_redirects=False)
    from urllib.parse import urlparse, parse_qs
    state = parse_qs(urlparse(connect.headers["location"]).query)["state"][0]

    callback = logged_in_client.get(f"/admin/api/calendar-sync/callback?code=abc123&state={state}")
    assert callback.status_code == 200, callback.text
    body = callback.json()
    assert body["calendars"] == [{"id": "primary", "summary": "Primary", "primary": True}]
    credential_id = body["credential_id"]

    status_before = logged_in_client.get("/admin/api/calendar-sync/status").json()
    assert status_before["connected"] is False  # calendar not chosen yet

    select = logged_in_client.post("/admin/api/calendar-sync/select", json={
        "credential_id": credential_id, "calendar_id": "primary",
    })
    assert select.status_code == 200

    status_after = logged_in_client.get("/admin/api/calendar-sync/status").json()
    assert status_after["connected"] is True
    assert status_after["calendar_id"] == "primary"


def test_reconnect_keeps_old_credential_active_until_new_one_is_selected(logged_in_client, monkeypatch):
    """Regression test for the outage window this used to have: an
    admin reconnecting (new Google account, fixing a revoked token)
    must not lose calendar sync the instant they complete the OAuth
    callback — the old, working credential should stay active right up
    until a new calendar is actually chosen, since select_calendar is
    what makes the switch atomic. Confirmed this fails without the fix
    (status_after_callback showed connected=False)."""
    old_credential_id = _create_active_credential(calendar_id="old-calendar@group.calendar.google.com")
    _enable_sync()
    _configure_oauth_client(logged_in_client)

    monkeypatch.setattr(
        "app.google_calendar_client.exchange_code",
        lambda **kw: {"access_token": "at-new", "refresh_token": "rt-new", "expires_in": 3600},
    )
    monkeypatch.setattr(
        "app.google_calendar_client.list_calendars",
        lambda access_token: [{"id": "new-calendar@group.calendar.google.com", "summary": "New", "primary": True}],
    )

    connect = logged_in_client.get("/admin/api/calendar-sync/connect", follow_redirects=False)
    from urllib.parse import urlparse, parse_qs
    state = parse_qs(urlparse(connect.headers["location"]).query)["state"][0]

    callback = logged_in_client.get(f"/admin/api/calendar-sync/callback?code=abc123&state={state}")
    assert callback.status_code == 200, callback.text
    new_credential_id = callback.json()["credential_id"]

    # The admin hasn't picked a calendar for the new connection yet -
    # the old one must still be the one in effect.
    status_mid_flow = logged_in_client.get("/admin/api/calendar-sync/status").json()
    assert status_mid_flow["connected"] is True
    assert status_mid_flow["calendar_id"] == "old-calendar@group.calendar.google.com"

    with session_scope() as db:
        old = db.get(CalendarCredential, old_credential_id)
        assert old.is_active is True

    select = logged_in_client.post("/admin/api/calendar-sync/select", json={
        "credential_id": new_credential_id, "calendar_id": "new-calendar@group.calendar.google.com",
    })
    assert select.status_code == 200

    # Now, and only now, does the handoff happen — atomically.
    with session_scope() as db:
        old = db.get(CalendarCredential, old_credential_id)
        new = db.get(CalendarCredential, new_credential_id)
        assert old.is_active is False
        assert new.is_active is True

    status_after = logged_in_client.get("/admin/api/calendar-sync/status").json()
    assert status_after["connected"] is True
    assert status_after["calendar_id"] == "new-calendar@group.calendar.google.com"


def test_callback_without_refresh_token_rejected(logged_in_client, monkeypatch):
    _configure_oauth_client(logged_in_client)
    monkeypatch.setattr(
        "app.google_calendar_client.exchange_code",
        lambda **kw: {"access_token": "at-only", "expires_in": 3600},  # no refresh_token
    )
    connect = logged_in_client.get("/admin/api/calendar-sync/connect", follow_redirects=False)
    from urllib.parse import urlparse, parse_qs
    state = parse_qs(urlparse(connect.headers["location"]).query)["state"][0]

    callback = logged_in_client.get(f"/admin/api/calendar-sync/callback?code=abc&state={state}")
    assert callback.status_code == 400


def test_disconnect_removes_credential_even_if_revoke_fails(logged_in_client, monkeypatch):
    monkeypatch.setattr("app.google_calendar_client.revoke_token", lambda token: False)
    _create_active_credential()

    resp = logged_in_client.post("/admin/api/calendar-sync/disconnect")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    status = logged_in_client.get("/admin/api/calendar-sync/status").json()
    assert status["connected"] is False


def test_disconnect_with_nothing_connected_404(logged_in_client):
    resp = logged_in_client.post("/admin/api/calendar-sync/disconnect")
    assert resp.status_code == 404


def test_calendar_sync_endpoints_require_auth(client):
    assert client.get("/admin/api/calendar-sync/status").status_code == 401


# ── Busy-time blocking in slot generation ───────────────────────────

def test_busy_block_removes_overlapping_slot_leaves_adjacent(logged_in_client, client, monkeypatch):
    _enable_sync()
    _create_active_credential()
    date = _nth_future_workday(250)

    def fake_busy(access_token, *, calendar_id, time_min, time_max):
        start = dt.datetime.combine(dt.date.fromisoformat(date), dt.time(10, 0), tzinfo=time_min.tzinfo)
        end = start + dt.timedelta(minutes=30)
        return [(start.isoformat(), end.isoformat())]

    monkeypatch.setattr("app.google_calendar_client.get_busy_times", fake_busy)

    slots = client.get(f"/api/booking/slots?date={date}").json()["slots"]
    assert "10:00" not in slots
    assert "09:30" in slots
    assert "10:30" in slots


def test_sync_disabled_ignores_busy_times(client, monkeypatch):
    # features.calendar_sync_enabled defaults False - no credential even
    # configured, so get_busy_times must never be called.
    called = []
    monkeypatch.setattr("app.google_calendar_client.get_busy_times", lambda *a, **k: called.append(1) or [])
    date = _nth_future_workday(251)
    client.get(f"/api/booking/slots?date={date}")
    assert called == []


def test_fail_closed_default_returns_no_slots_on_api_failure(client, monkeypatch):
    _enable_sync()
    _create_active_credential()
    date = _nth_future_workday(252)

    def boom(*a, **k):
        from app.google_calendar_client import GoogleCalendarError
        raise GoogleCalendarError("simulated outage")

    monkeypatch.setattr("app.google_calendar_client.get_busy_times", boom)
    resp = client.get(f"/api/booking/slots?date={date}")
    assert resp.status_code == 200
    assert resp.json()["slots"] == []  # safe default: can't confirm real availability


def test_fail_open_setting_ignores_api_failure(logged_in_client, client, monkeypatch):
    _enable_sync()
    _create_active_credential()
    with session_scope() as db:
        set_setting(db, "booking.calendar_sync_fail_open", True, actor_id=None, actor_username="test")
    date = _nth_future_workday(253)

    def boom(*a, **k):
        from app.google_calendar_client import GoogleCalendarError
        raise GoogleCalendarError("simulated outage")

    monkeypatch.setattr("app.google_calendar_client.get_busy_times", boom)
    resp = client.get(f"/api/booking/slots?date={date}")
    assert resp.status_code == 200
    assert len(resp.json()["slots"]) > 0  # ignored the failure, fell back to normal availability


def test_no_calendar_selected_yet_does_not_block_slots(client):
    """A credential can exist mid-connect (calendar_id not chosen,
    is_active False) - that must never be treated as 'connected'."""
    _enable_sync()
    _create_active_credential(calendar_id=None)
    with session_scope() as db:
        cred = db.query(CalendarCredential).first()
        cred.is_active = False
    date = _nth_future_workday(254)
    resp = client.get(f"/api/booking/slots?date={date}")
    assert resp.status_code == 200
    assert len(resp.json()["slots"]) > 0


def test_expired_token_is_refreshed_before_freebusy_call(client, monkeypatch):
    _enable_sync()
    cred_id = _create_active_credential(expires_in_future=False)
    date = _nth_future_workday(255)

    refresh_calls = []
    busy_calls = []

    def fake_refresh(*, client_id, client_secret, refresh_token):
        refresh_calls.append(refresh_token)
        return {"access_token": "refreshed-access-token", "expires_in": 3600}

    def fake_busy(access_token, *, calendar_id, time_min, time_max):
        busy_calls.append(access_token)
        return []

    with session_scope() as db:
        set_setting(db, "calendar_sync.google_client_id", "cid", actor_id=None, actor_username="test")
        set_setting(db, "calendar_sync.google_client_secret", "csecret", actor_id=None, actor_username="test")

    monkeypatch.setattr("app.google_calendar_client.refresh_access_token", fake_refresh)
    monkeypatch.setattr("app.google_calendar_client.get_busy_times", fake_busy)

    resp = client.get(f"/api/booking/slots?date={date}")
    assert resp.status_code == 200
    assert len(refresh_calls) == 1
    assert busy_calls == ["refreshed-access-token"]

    with session_scope() as db:
        cred = db.get(CalendarCredential, cred_id)
        expires_at = cred.token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
        assert expires_at > dt.datetime.now(dt.timezone.utc)


# ── Event creation on confirm ────────────────────────────────────────

def test_event_created_on_confirmed_booking(client, monkeypatch):
    _enable_sync()
    _create_active_credential()
    date = _nth_future_workday(256)

    created = []
    monkeypatch.setattr("app.google_calendar_client.get_busy_times", lambda *a, **k: [])
    monkeypatch.setattr("app.google_calendar_client.create_event", lambda *a, **kw: created.append(kw) or "gcal-evt-1")

    resp = client.post("/api/booking/appointments", json={"date": date, "slot": "09:00", **VALID_APPT})
    body = resp.json()
    assert body["ok"] is True
    assert body["appointment"]["external_event_id"] == "gcal-evt-1"
    assert len(created) == 1


def test_event_creation_failure_does_not_break_booking(client, monkeypatch):
    _enable_sync()
    _create_active_credential()
    date = _nth_future_workday(257)

    def boom(*a, **k):
        from app.google_calendar_client import GoogleCalendarError
        raise GoogleCalendarError("simulated failure")

    monkeypatch.setattr("app.google_calendar_client.get_busy_times", lambda *a, **k: [])
    monkeypatch.setattr("app.google_calendar_client.create_event", boom)

    resp = client.post("/api/booking/appointments", json={"date": date, "slot": "09:00", **VALID_APPT})
    body = resp.json()
    assert body["ok"] is True
    assert body["appointment"]["external_event_id"] is None


def test_event_created_only_on_confirmation_accept_not_on_pending_request(logged_in_client, client, monkeypatch):
    _enable_sync()
    _create_active_credential()
    svc = logged_in_client.post("/admin/api/services", json={
        "name": "Sync Confirmation Service", "duration_minutes": 30, "requires_confirmation": True,
    }).json()
    date = _nth_future_workday(258)

    created = []
    monkeypatch.setattr("app.google_calendar_client.get_busy_times", lambda *a, **k: [])
    monkeypatch.setattr("app.google_calendar_client.create_event", lambda *a, **kw: created.append(kw) or "gcal-evt-2")

    booked = client.post("/api/booking/appointments", json={
        "date": date, "slot": "09:00", "service_id": svc["id"], **VALID_APPT,
    }).json()["appointment"]
    assert booked["external_event_id"] is None
    assert len(created) == 0  # pending - no event yet

    logged_in_client.post(f"/admin/api/booking/appointments/{booked['id']}/accept")
    assert len(created) == 1  # now confirmed


def test_event_deleted_on_self_service_cancel(client, monkeypatch):
    _enable_sync()
    _create_active_credential()
    date = _nth_future_workday(259)

    deleted = []
    monkeypatch.setattr("app.google_calendar_client.get_busy_times", lambda *a, **k: [])
    monkeypatch.setattr("app.google_calendar_client.create_event", lambda *a, **k: "gcal-evt-3")
    monkeypatch.setattr("app.google_calendar_client.delete_event", lambda *a, **kw: deleted.append(kw))

    created = client.post("/api/booking/appointments", json={"date": date, "slot": "09:00", **VALID_APPT}).json()

    resp = client.post("/api/booking/appointments/cancel", json={"id": created["id"], "email": VALID_APPT["email"]})
    assert resp.json()["ok"] is True
    assert len(deleted) == 1
    assert deleted[0]["event_id"] == "gcal-evt-3"


def test_event_updated_in_place_on_reschedule(client, monkeypatch):
    _enable_sync()
    _create_active_credential()
    date = _nth_future_workday(160)
    new_date = _nth_future_workday(161)

    create_calls = []
    update_calls = []
    delete_calls = []
    monkeypatch.setattr("app.google_calendar_client.get_busy_times", lambda *a, **k: [])
    monkeypatch.setattr("app.google_calendar_client.create_event",
                         lambda *a, **kw: create_calls.append(kw) or f"gcal-evt-{len(create_calls)}")
    monkeypatch.setattr("app.google_calendar_client.update_event",
                         lambda *a, **kw: update_calls.append(kw) or kw["event_id"])
    monkeypatch.setattr("app.google_calendar_client.delete_event", lambda *a, **kw: delete_calls.append(kw))

    created = client.post("/api/booking/appointments", json={"date": date, "slot": "09:00", **VALID_APPT}).json()
    assert created["appointment"]["external_event_id"] == "gcal-evt-1"

    resp = client.post("/api/booking/appointments/reschedule", json={
        "id": created["id"], "email": VALID_APPT["email"], "date": new_date, "time": "10:00",
    })
    body = resp.json()
    assert body["ok"] is True
    # PATCHes the existing event in place — same event id, no
    # delete-then-recreate churn.
    assert len(update_calls) == 1
    assert update_calls[0]["event_id"] == "gcal-evt-1"
    assert len(create_calls) == 1  # only the original creation, never a second
    assert len(delete_calls) == 0
    assert body["appointment"]["external_event_id"] == "gcal-evt-1"


def test_event_recreated_on_reschedule_if_update_fails(client, monkeypatch):
    """If the linked event is gone on Google's side (e.g. deleted
    directly in Google Calendar), the PATCH 404s and reschedule falls
    back to recreating the event rather than leaving the appointment
    silently unsynced."""
    _enable_sync()
    _create_active_credential()
    date = _nth_future_workday(162)
    new_date = _nth_future_workday(163)

    create_calls = []
    monkeypatch.setattr("app.google_calendar_client.get_busy_times", lambda *a, **k: [])
    monkeypatch.setattr("app.google_calendar_client.create_event",
                         lambda *a, **kw: create_calls.append(kw) or f"gcal-evt-{len(create_calls)}")

    def boom_update(*a, **kw):
        from app.google_calendar_client import GoogleCalendarError
        raise GoogleCalendarError("simulated 404 — event no longer exists", status_code=404)

    monkeypatch.setattr("app.google_calendar_client.update_event", boom_update)

    created = client.post("/api/booking/appointments", json={"date": date, "slot": "09:00", **VALID_APPT}).json()
    assert created["appointment"]["external_event_id"] == "gcal-evt-1"

    resp = client.post("/api/booking/appointments/reschedule", json={
        "id": created["id"], "email": VALID_APPT["email"], "date": new_date, "time": "10:00",
    })
    body = resp.json()
    assert body["ok"] is True
    assert len(create_calls) == 2  # original + the fallback recreate
    assert body["appointment"]["external_event_id"] == "gcal-evt-2"


def test_event_not_recreated_on_reschedule_if_update_fails_for_other_reason(client, monkeypatch):
    """Regression test: a transient failure (rate limit, timeout, 500 —
    anything that isn't specifically a 404) during the reschedule PATCH
    must NOT fall back to recreating the event. The original is
    presumably still sitting on the calendar untouched; blindly
    recreating on every failure used to leave that original orphaned
    while creating a duplicate alongside it. Confirmed this fails
    without the fix (create_calls ends up at 2, a duplicate, instead of
    staying at 1)."""
    _enable_sync()
    _create_active_credential()
    date = _nth_future_workday(145)
    new_date = _nth_future_workday(146)

    create_calls = []
    monkeypatch.setattr("app.google_calendar_client.get_busy_times", lambda *a, **k: [])
    monkeypatch.setattr("app.google_calendar_client.create_event",
                         lambda *a, **kw: create_calls.append(kw) or f"gcal-evt-{len(create_calls)}")

    def boom_update(*a, **kw):
        from app.google_calendar_client import GoogleCalendarError
        raise GoogleCalendarError("simulated rate limit", status_code=429)

    monkeypatch.setattr("app.google_calendar_client.update_event", boom_update)

    created = client.post("/api/booking/appointments", json={"date": date, "slot": "09:00", **VALID_APPT}).json()
    assert created["appointment"]["external_event_id"] == "gcal-evt-1"

    resp = client.post("/api/booking/appointments/reschedule", json={
        "id": created["id"], "email": VALID_APPT["email"], "date": new_date, "time": "10:00",
    })
    body = resp.json()
    # The reschedule itself still succeeds — it's the calendar push that
    # failed, best-effort, and must never block the booking outcome.
    assert body["ok"] is True
    assert len(create_calls) == 1  # only the original — no duplicate
    # The stale link is left alone (not cleared, not repointed) so a
    # retry or the next drift check has something to act on.
    assert body["appointment"]["external_event_id"] == "gcal-evt-1"


# ── Admin-side reschedule/edit ───────────────────────────────────────

def test_admin_reschedule_updates_event_in_place(logged_in_client, client, monkeypatch):
    _enable_sync()
    _create_active_credential()
    date = _nth_future_workday(164)
    new_date = _nth_future_workday(165)

    update_calls = []
    monkeypatch.setattr("app.google_calendar_client.get_busy_times", lambda *a, **k: [])
    monkeypatch.setattr("app.google_calendar_client.create_event", lambda *a, **kw: "gcal-evt-1")
    monkeypatch.setattr("app.google_calendar_client.update_event",
                         lambda *a, **kw: update_calls.append(kw) or kw["event_id"])

    created = client.post("/api/booking/appointments", json={"date": date, "slot": "09:00", **VALID_APPT}).json()

    resp = logged_in_client.post(
        f"/admin/api/booking/appointments/{created['id']}/reschedule",
        json={"date": new_date, "time": "10:00"},
    )
    body = resp.json()
    assert resp.status_code == 200, resp.text
    assert body["ok"] is True
    assert body["appointment"]["date"] == new_date
    assert body["appointment"]["time"] == "10:00"
    assert len(update_calls) == 1
    assert update_calls[0]["event_id"] == "gcal-evt-1"


def test_admin_reschedule_requires_open_slot(logged_in_client, client):
    date = _nth_future_workday(166)
    first = client.post("/api/booking/appointments", json={"date": date, "slot": "09:00", **VALID_APPT}).json()
    second = client.post("/api/booking/appointments", json={
        "date": date, "slot": "09:30", "name": "Sam Lee", "email": "sam@example.com", "phone": "555-0101",
    }).json()

    resp = logged_in_client.post(
        f"/admin/api/booking/appointments/{first['id']}/reschedule",
        json={"date": date, "time": "09:30"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "slot_unavailable"


# ── Manual calendar event management ─────────────────────────────────

def test_manual_event_crud(logged_in_client, monkeypatch):
    _create_active_credential()

    created_calls, updated_calls, deleted_calls = [], [], []
    monkeypatch.setattr("app.google_calendar_client.create_event",
                         lambda *a, **kw: created_calls.append(kw) or "manual-evt-1")
    monkeypatch.setattr("app.google_calendar_client.update_event",
                         lambda *a, **kw: updated_calls.append(kw) or kw["event_id"])
    monkeypatch.setattr("app.google_calendar_client.delete_event",
                         lambda *a, **kw: deleted_calls.append(kw))
    monkeypatch.setattr("app.google_calendar_client.list_all_events", lambda *a, **kw: ([
        {"id": "manual-evt-1", "summary": "Staff meeting",
         "start": {"dateTime": "2026-09-01T10:00:00+00:00"}, "end": {"dateTime": "2026-09-01T11:00:00+00:00"}},
    ], None))

    create_resp = logged_in_client.post("/admin/api/calendar-events", json={
        "summary": "Staff meeting", "description": "Weekly sync",
        "start": "2026-09-01T10:00:00", "end": "2026-09-01T11:00:00", "timezone": "UTC",
    })
    assert create_resp.status_code == 200, create_resp.text
    assert create_resp.json()["id"] == "manual-evt-1"
    assert len(created_calls) == 1

    list_resp = logged_in_client.get("/admin/api/calendar-events?date_from=2026-09-01&date_to=2026-09-07")
    assert list_resp.status_code == 200, list_resp.text
    events = list_resp.json()
    assert len(events) == 1
    assert events[0]["id"] == "manual-evt-1"

    update_resp = logged_in_client.patch("/admin/api/calendar-events/manual-evt-1", json={
        "summary": "Staff meeting (moved)", "description": "Weekly sync",
        "start": "2026-09-01T14:00:00", "end": "2026-09-01T15:00:00", "timezone": "UTC",
    })
    assert update_resp.status_code == 200, update_resp.text
    assert len(updated_calls) == 1

    delete_resp = logged_in_client.delete("/admin/api/calendar-events/manual-evt-1")
    assert delete_resp.status_code == 200, delete_resp.text
    assert len(deleted_calls) == 1


def test_manual_event_endpoints_require_connected_calendar(logged_in_client):
    resp = logged_in_client.post("/admin/api/calendar-events", json={
        "summary": "Test", "start": "2026-09-01T10:00:00", "end": "2026-09-01T11:00:00", "timezone": "UTC",
    })
    assert resp.status_code == 400


# ── Two-way drift detection ───────────────────────────────────────────

def test_sync_now_flags_externally_deleted_event(logged_in_client, client, monkeypatch):
    _enable_sync()
    _create_active_credential()
    date = _nth_future_workday(167)

    monkeypatch.setattr("app.google_calendar_client.get_busy_times", lambda *a, **k: [])
    monkeypatch.setattr("app.google_calendar_client.create_event", lambda *a, **kw: "gcal-evt-drift-1")

    created = client.post("/api/booking/appointments", json={"date": date, "slot": "09:00", **VALID_APPT}).json()

    monkeypatch.setattr("app.google_calendar_client.list_all_events", lambda *a, **kw: ([
        {"id": "gcal-evt-drift-1", "status": "cancelled"},
    ], "next-token-1"))

    resp = logged_in_client.post("/admin/api/calendar-sync/sync-now")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["flagged"] == 1

    lookup = client.post("/api/booking/appointments/lookup", json={
        "id": created["id"], "email": VALID_APPT["email"],
    }).json()
    assert lookup["appointment"]["calendar_drift"]


def test_sync_now_flags_externally_changed_time(logged_in_client, client, monkeypatch):
    _enable_sync()
    _create_active_credential()
    date = _nth_future_workday(168)

    monkeypatch.setattr("app.google_calendar_client.get_busy_times", lambda *a, **k: [])
    monkeypatch.setattr("app.google_calendar_client.create_event", lambda *a, **kw: "gcal-evt-drift-2")

    created = client.post("/api/booking/appointments", json={"date": date, "slot": "09:00", **VALID_APPT}).json()

    monkeypatch.setattr("app.google_calendar_client.list_all_events", lambda *a, **kw: ([
        {"id": "gcal-evt-drift-2", "status": "confirmed",
         "start": {"dateTime": f"{date}T14:00:00+00:00"}, "end": {"dateTime": f"{date}T14:30:00+00:00"}},
    ], "next-token-2"))

    resp = logged_in_client.post("/admin/api/calendar-sync/sync-now")
    assert resp.json()["flagged"] == 1

    status = logged_in_client.get("/admin/api/calendar-sync/status").json()
    # >= rather than == : an earlier test in this module (deliberately)
    # leaves its own flagged appointment in place, since the drift
    # column has no reason to be cleared by an unrelated test's
    # teardown — this test only needs to know its own flag landed.
    assert status["flagged_count"] >= 1

    lookup = client.post("/api/booking/appointments/lookup", json={
        "id": created["id"], "email": VALID_APPT["email"],
    }).json()
    assert lookup["appointment"]["calendar_drift"]


def test_sync_now_not_connected(logged_in_client):
    resp = logged_in_client.post("/admin/api/calendar-sync/sync-now")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["error"] == "not_connected"


def test_drift_check_uses_appointment_own_timezone_not_live_setting(logged_in_client, client, monkeypatch):
    """Regression test: booking.timezone changing after an appointment
    exists must not make detect_drift falsely flag it as changed on
    Google when nothing actually moved. Appointment.timezone (snapshotted
    at booking time) is what closes this — without it, detect_drift
    reinterprets the stored date/time under whatever booking.timezone
    currently is, which is a different zone here on purpose."""
    _enable_sync()
    _create_active_credential()
    date = _nth_future_workday(169)

    with session_scope() as db:
        set_setting(db, "booking.timezone", "America/New_York", actor_id=None, actor_username="test-setup")

    monkeypatch.setattr("app.google_calendar_client.get_busy_times", lambda *a, **k: [])
    monkeypatch.setattr("app.google_calendar_client.create_event", lambda *a, **kw: "gcal-evt-tz-1")

    created = client.post("/api/booking/appointments", json={"date": date, "slot": "09:00", **VALID_APPT}).json()
    assert created["appointment"]["timezone"] == "America/New_York"

    # The business's configured timezone changes (new location, a
    # correction, whatever) — the appointment above was booked before
    # this change and must keep being read back in the zone it was
    # actually booked under.
    with session_scope() as db:
        set_setting(db, "booking.timezone", "Asia/Tokyo", actor_id=None, actor_username="test-setup")

    from zoneinfo import ZoneInfo
    start_local = dt.datetime.combine(dt.date.fromisoformat(date), dt.time(9, 0), tzinfo=ZoneInfo("America/New_York"))
    end_local = start_local + dt.timedelta(minutes=30)
    # The event on Google is exactly what it should be — nothing changed there.
    monkeypatch.setattr("app.google_calendar_client.list_all_events", lambda *a, **kw: ([
        {"id": "gcal-evt-tz-1", "status": "confirmed",
         "start": {"dateTime": start_local.isoformat()}, "end": {"dateTime": end_local.isoformat()}},
    ], "next-token-tz"))

    resp = logged_in_client.post("/admin/api/calendar-sync/sync-now")
    assert resp.status_code == 200, resp.text
    assert resp.json()["flagged"] == 0

    lookup = client.post("/api/booking/appointments/lookup", json={
        "id": created["id"], "email": VALID_APPT["email"],
    }).json()
    assert not lookup["appointment"]["calendar_drift"]


