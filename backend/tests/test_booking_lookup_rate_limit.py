"""Regression test for the missing rate limit on /appointments/lookup —
read-only, but a confirmation code + guessed/known email is a plausible
enumeration target, so it shouldn't be callable an unlimited number of
times per IP either."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.rate_limit import limiter


def test_lookup_is_rate_limited():
    limiter.reset()  # RATE_LIMIT_LOOKUP is keyed by IP; every TestClient shares one fake IP
    c = TestClient(app)
    body = {"id": "PRN-NOTREAL1", "email": "nobody@example.com"}

    for _ in range(20):  # RATE_LIMIT_LOOKUP = "20/hour" (config.py)
        resp = c.post("/api/booking/appointments/lookup", json=body)
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"ok": False, "error": "not_found"}

    resp = c.post("/api/booking/appointments/lookup", json=body)
    assert resp.status_code == 429, resp.text
    limiter.reset()
