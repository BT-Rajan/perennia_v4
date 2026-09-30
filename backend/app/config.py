"""
Infrastructure settings — loaded once, at process start, from environment
variables (.env in dev).

DELIBERATE SCOPE: this file holds only things that (a) are secrets, or
(b) must be known before a database connection exists, so they *cannot*
live in the DB-backed settings registry. Everything else — every piece of
site content, every business rule, every toggle an admin should be able to
change without a deploy — belongs in `settings_registry.py` and the
`site_setting` table instead. If you're tempted to add a new field here,
ask first: "could this be a runtime admin setting?" If yes, it goes in the
registry, not here. This split is what keeps this file small across all
10 passes instead of growing into the 500-line settings god-object the
reference app has.

No secret has a hardcoded default that would work in production — a
missing required var fails startup loudly instead of running insecurely.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
# override=True: this server also runs other apps, and python-dotenv's
# default behavior is to NOT overwrite a DATABASE_URL (or any var) that's
# already present in the OS environment. Without override=True, a stray
# env var from another app/service on this box silently wins over this
# app's own .env, and the backend ends up talking to the wrong database
# (or falling back to the SQLite default) with no error at all.
load_dotenv(BASE_DIR / ".env", override=True)


def _fail(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


class InfraSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    # --- Environment -------------------------------------------------
    ENVIRONMENT: str = "development"  # development | production

    # --- Database ------------------------------------------------------
    # SQLite by default (zero-config local/dev). Point this at a
    # postgres:// or mysql:// URL in production — nothing else in the
    # codebase assumes a specific engine, SQLAlchemy handles the dialect.
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'perennia.db'}"

    # --- Network ---------------------------------------------------------
    HOST: str = "127.0.0.1"
    PORT: int = 8001
    # Comma-separated list of origins allowed to call the API. Same-origin
    # requests don't need this; keep it explicit rather than "*".
    ALLOWED_ORIGINS: str = ""

    # --- Secrets (required — the app refuses to start without these) ----
    # Signs session cookies / CSRF tokens.
    SECRET_KEY: str = ""
    # Encrypts secret-typed settings (API keys, SMTP passwords, etc.) at
    # rest in the DB. Generate both with scripts/gen_secrets.py.
    ENCRYPTION_KEY: str = ""

    # --- Bootstrap admin (first run only) --------------------------------
    # Used ONLY by scripts/init_db.py to create the first admin account if
    # none exists yet. Ignored on every subsequent start — after that,
    # admin accounts and their password hashes live in the DB and are
    # managed from the admin panel itself (see Pass 9).
    BOOTSTRAP_ADMIN_USERNAME: str = "admin"
    BOOTSTRAP_ADMIN_PASSWORD_HASH: str = ""

    SESSION_TTL_SECONDS: int = 3600
    # Only false for local http-only dev — Secure cookies are silently
    # dropped by browsers over plain HTTP.
    COOKIE_SECURE: bool = True

    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_APPOINTMENT: str = "6/hour"
    # Lookup is read-only (id + email -> appointment details) so it gets
    # a looser cap than the mutating booking actions above, but it was
    # previously uncapped entirely: a 16-char confirmation code plus a
    # guessed or already-known email is a plausible enumeration target,
    # and without any limit here a client could hammer it indefinitely.
    RATE_LIMIT_LOOKUP: str = "20/hour"
    RATE_LIMIT_KNOWLEDGE_UPLOAD: str = "10/hour"

    LOG_DIR: Path = BASE_DIR / "logs"
    DATA_DIR: Path = BASE_DIR / "data"

    # Uploaded brand assets (logo, favicon). Served as static files —
    # nothing secret is ever allowed to live under this directory.
    UPLOADS_DIR: Path = BASE_DIR / "data" / "uploads"
    MAX_UPLOAD_IMAGE_BYTES: int = 4 * 1024 * 1024  # 4 MB

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


def _validate(s: InfraSettings) -> InfraSettings:
    if s.is_production:
        if not s.SECRET_KEY or len(s.SECRET_KEY) < 32:
            _fail("SECRET_KEY must be set (>=32 chars) in production. Run scripts/gen_secrets.py.")
        if not s.ENCRYPTION_KEY:
            _fail("ENCRYPTION_KEY must be set in production. Run scripts/gen_secrets.py.")
        if s.DATABASE_URL.startswith("sqlite") :
            print("WARNING: running production with SQLite — fine for small sites, "
                  "but consider Postgres/MySQL for concurrent write load.", file=sys.stderr)
        if not s.COOKIE_SECURE:
            _fail("COOKIE_SECURE must be true in production.")
    else:
        # Dev: auto-generate ephemeral secrets so `uvicorn app.main:app` just
        # works out of the box, but never silently do this in prod.
        if not s.SECRET_KEY:
            import secrets
            s.SECRET_KEY = secrets.token_urlsafe(48)
        if not s.ENCRYPTION_KEY:
            from cryptography.fernet import Fernet
            s.ENCRYPTION_KEY = Fernet.generate_key().decode()

    if not re.match(r"^(sqlite|postgresql|mysql)", s.DATABASE_URL):
        _fail(f"Unsupported DATABASE_URL scheme: {s.DATABASE_URL!r}")

    return s


settings = _validate(InfraSettings())
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
