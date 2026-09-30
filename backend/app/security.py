"""
Security primitives, isolated in one module so every other file uses
these instead of rolling its own crypto:

- Password hashing: bcrypt via passlib (adaptive cost, salted).
- Session cookies: itsdangerous signs an opaque session id — the cookie
  itself carries no user data, so tampering with it just invalidates the
  signature; the actual session (and its expiry, so it can be revoked
  server-side) lives in the `admin_session` table.
- Secret settings (API keys, SMTP passwords, ...) are encrypted at rest
  with Fernet (AES-128-CBC + HMAC) using ENCRYPTION_KEY, so a DB leak
  alone doesn't leak third-party credentials.
"""
from __future__ import annotations

import hmac

from cryptography.fernet import Fernet, InvalidToken
from itsdangerous import BadSignature, URLSafeTimedSerializer
from passlib.context import CryptContext

from app.config import settings

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
_signer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="admin-session")
_oauth_state_signer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="calendar-sync-oauth-state")
_fernet = Fernet(settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY)

SESSION_COOKIE_NAME = "perennia_admin_session"


# ── Passwords ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return _pwd_ctx.verify(plain, hashed)
    except ValueError:
        return False


# ── Session cookie signing ───────────────────────────────────────────
# The cookie payload is just the session row's opaque id; signing proves
# it wasn't tampered with, DB lookup proves it hasn't expired/been revoked.

def sign_session_id(session_id: str) -> str:
    return _signer.dumps(session_id)


def unsign_session_id(cookie_value: str, max_age: int) -> str | None:
    try:
        return _signer.loads(cookie_value, max_age=max_age)
    except BadSignature:
        return None


# ── OAuth state signing (Pass 12: Calendar Sync connect flow) ──────────
# Google's OAuth `state` parameter is our only CSRF/tampering defense
# across the redirect round-trip to Google and back — a signed,
# timestamped opaque token (the admin's id, so the callback can attribute
# the connection to who initiated it) rather than a DB row, since the
# whole point is it only needs to survive one redirect and expire fast.

def sign_oauth_state(admin_id: str) -> str:
    return _oauth_state_signer.dumps(admin_id)


def unsign_oauth_state(state: str, max_age: int = 600) -> str | None:
    try:
        return _oauth_state_signer.loads(state, max_age=max_age)
    except BadSignature:
        return None


# ── CSRF ────────────────────────────────────────────────────────────────
# Token generation itself is AdminSession.csrf_token's column default
# (see app/models.py) — this module only verifies.

def csrf_tokens_match(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return hmac.compare_digest(a, b)


# ── Secret-at-rest encryption (for site_setting.is_secret rows) ────────

def encrypt_secret(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    try:
        return _fernet.decrypt(token.encode()).decode()
    except InvalidToken:
        raise ValueError("Could not decrypt secret value — ENCRYPTION_KEY may have changed.")
