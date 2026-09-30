"""
Shared test fixtures. test_calendar_sync.py (and any future test file)
depends on `client` and `logged_in_client` — this is where they live.

DB ISOLATION: app/config.py's own comment says "the suite spins up a
fresh temp-file SQLite DB per run" (see app/main.py's
_start_background_jobs, which already special-cases `"pytest" in
sys.modules`), but nothing actually did that — this file is what was
missing. Every line below the module docstring runs before any `app.*`
module is imported, which matters: app.config.py calls
load_dotenv(..., override=True) at import time, which would otherwise
overwrite the DATABASE_URL below with whatever a real backend/.env
points at (e.g. a shared production MySQL box) the moment app.config
is first imported — so dotenv.load_dotenv is patched to a no-op first,
guaranteeing this suite can never accidentally run against a real
database no matter what's on disk.
"""
from __future__ import annotations

import os
import secrets
import tempfile
from pathlib import Path

_TEST_DB_PATH = Path(tempfile.mkdtemp(prefix="perennia-test-")) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ["ENVIRONMENT"] = "development"  # keeps _validate()'s dev branch, which auto-generates SECRET_KEY/ENCRYPTION_KEY
os.environ["COOKIE_SECURE"] = "false"      # TestClient isn't https; a Secure cookie would be silently dropped

import dotenv  # noqa: E402 — see module docstring for why this precedes the app.* imports below
dotenv.load_dotenv = lambda *a, **k: False  # no-op: stop app.config from re-reading a real .env over the top of this

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine, session_scope  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AdminUser  # noqa: E402
from app.rate_limit import limiter  # noqa: E402
from app.security import hash_password  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _test_schema():
    """Creates every table against the throwaway DB above once per test
    session, and drops it all afterward. Not reset between individual
    tests — test_calendar_sync.py already manages its own cross-test
    state explicitly (see its _clear_calendar_state_after_test and
    _widen_booking_window fixtures), which assumes a persistent schema
    across the run rather than a fresh one per test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    """An unauthenticated API client, for public (non-admin) endpoints."""
    return TestClient(app)


@pytest.fixture
def logged_in_client() -> TestClient:
    """An API client logged in as a fresh bootstrap admin, with the CSRF
    token from login already attached as a default header — tests call
    logged_in_client.post(...)/put(...)/etc. directly without handling
    the login round-trip or require_csrf's X-CSRF-Token header
    themselves. A new admin user per test (cheap, and avoids tests
    needing to coordinate over a shared one)."""
    username = f"test-admin-{secrets.token_hex(4)}"
    password = secrets.token_urlsafe(16)
    with session_scope() as db:
        db.add(AdminUser(username=username, password_hash=hash_password(password), role="owner"))

    # RATE_LIMIT_LOGIN ("5/minute") is keyed by client IP, and every
    # TestClient request comes from the same fake IP — without this,
    # the 6th test in the whole run to request logged_in_client would
    # 429 on its own login, not because of anything it did wrong.
    limiter.reset()

    c = TestClient(app)
    resp = c.post("/admin/api/auth/login", json={"username": username, "password": password})
    resp.raise_for_status()
    c.headers.update({"X-CSRF-Token": resp.json()["csrf_token"]})
    return c
