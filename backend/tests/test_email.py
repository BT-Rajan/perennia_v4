"""
SMTP sending: STARTTLS vs SSL by port, headers (incl. a non-ASCII
display name), the best-effort wrapper, and the admin "Send test
email" endpoint. smtplib's client classes are swapped for a recorder,
so nothing leaves the machine.
"""
from __future__ import annotations

import smtplib

import pytest

from app import notification_service
from app.db import session_scope
from app.models import SiteSetting
from app.settings_service import invalidate_cache, set_many

NOTIFICATION_KEYS = (
    "notifications.email_enabled", "notifications.smtp_host", "notifications.smtp_port",
    "notifications.smtp_username", "notifications.smtp_password", "notifications.smtp_use_tls",
    "notifications.from_email", "notifications.from_name", "notifications.admin_alert_email",
)


class FakeSMTP:
    instances: list["FakeSMTP"] = []
    fail_with: Exception | None = None

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.ssl = host, port, context is not None
        self.calls: list[str] = []
        self.sent = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.calls.append("quit")

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, username, password):
        self.calls.append(f"login:{username}:{password}")
        if FakeSMTP.fail_with:
            raise FakeSMTP.fail_with

    def send_message(self, msg):
        self.calls.append("send")
        self.sent.append(msg)


class FakeSMTPSSL(FakeSMTP):
    pass


@pytest.fixture(autouse=True)
def fake_smtp(monkeypatch):
    FakeSMTP.instances = []
    FakeSMTP.fail_with = None
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTPSSL)
    yield
    with session_scope() as db:
        for key in NOTIFICATION_KEYS:
            row = db.get(SiteSetting, key)
            if row is not None:
                db.delete(row)
    invalidate_cache()


def _configure(**overrides):
    values = {
        "notifications.smtp_host": "smtp.example.com",
        "notifications.smtp_port": 587,
        "notifications.smtp_username": "mailer@example.com",
        "notifications.smtp_password": "app-password",
        "notifications.smtp_use_tls": True,
        "notifications.from_email": "noreply@example.com",
        "notifications.from_name": "بيرينيا Perennia",
        **overrides,
    }
    with session_scope() as db:
        set_many(db, values, actor_id=None, actor_username="test")


def test_port_587_uses_starttls_then_login():
    _configure()
    with session_scope() as db:
        notification_service.deliver_email(db, to_email="a@b.com", subject="Hi", body_text="Body")
    (server,) = FakeSMTP.instances
    assert type(server) is FakeSMTP
    assert server.calls == ["starttls", "login:mailer@example.com:app-password", "send", "quit"]
    msg = server.sent[0]
    assert msg["To"] == "a@b.com"
    assert "noreply@example.com" in msg["From"]
    assert msg["Date"] and msg["Message-ID"].endswith("@example.com>")
    # Non-ASCII display name is RFC 2047-encoded on the wire, not raw UTF-8.
    wire = msg.as_bytes()
    assert b"=?utf-8?" in wire.split(b"\n\n", 1)[0].lower()
    assert msg.get_content().strip() == "Body"


def test_port_465_uses_ssl_without_starttls():
    _configure(**{"notifications.smtp_port": 465})
    with session_scope() as db:
        notification_service.deliver_email(db, to_email="a@b.com", subject="Hi", body_text="Body")
    (server,) = FakeSMTP.instances
    assert type(server) is FakeSMTPSSL and server.ssl
    assert "starttls" not in server.calls and "send" in server.calls


def test_no_username_skips_login():
    _configure(**{"notifications.smtp_username": "", "notifications.smtp_use_tls": False})
    with session_scope() as db:
        notification_service.deliver_email(db, to_email="a@b.com", subject="Hi", body_text="Body")
    assert FakeSMTP.instances[0].calls == ["send", "quit"]


def test_send_email_is_best_effort():
    _configure()
    with session_scope() as db:
        # Disabled: nothing sent.
        assert notification_service.send_email(db, to_email="a@b.com", subject="s", body_text="b") is False
    assert FakeSMTP.instances == []

    _configure(**{"notifications.email_enabled": True})
    FakeSMTP.fail_with = smtplib.SMTPAuthenticationError(535, b"bad creds")
    with session_scope() as db:
        assert notification_service.send_email(db, to_email="a@b.com", subject="s", body_text="b") is False

    FakeSMTP.fail_with = None
    with session_scope() as db:
        assert notification_service.send_email(db, to_email="a@b.com", subject="s", body_text="b") is True


def test_admin_test_email_endpoint(logged_in_client):
    resp = logged_in_client.post("/admin/api/settings/notifications/test-email", json={"to": "x@y.com"})
    assert resp.status_code == 400 and "SMTP host" in resp.json()["detail"]

    # Works while notifications are still switched off.
    _configure(**{"notifications.admin_alert_email": "ops@example.com"})
    resp = logged_in_client.post("/admin/api/settings/notifications/test-email", json={"to": ""})
    assert resp.status_code == 200 and resp.json() == {"sent": True, "to": "ops@example.com"}
    assert FakeSMTP.instances[-1].sent[0]["To"] == "ops@example.com"

    FakeSMTP.fail_with = smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")
    resp = logged_in_client.post("/admin/api/settings/notifications/test-email", json={"to": "x@y.com"})
    assert resp.status_code == 502 and "login failed (535)" in resp.json()["detail"]


def test_test_email_endpoint_requires_admin(client):
    resp = client.post("/admin/api/settings/notifications/test-email", json={"to": "x@y.com"})
    assert resp.status_code in (401, 403)
