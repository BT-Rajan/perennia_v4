#!/usr/bin/env python3
"""
Creates all tables (idempotent) and, only if the admin_user table is
empty, bootstraps one admin account from BOOTSTRAP_ADMIN_USERNAME /
BOOTSTRAP_ADMIN_PASSWORD_HASH in .env (generate the hash with
scripts/gen_secrets.py). Safe to re-run: it never touches existing
admin accounts.

    python scripts/init_db.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.config import settings
from app.db import Base, engine, session_scope
from app.models import AdminUser  # noqa: F401 — needed for Base.metadata


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print(f"Tables created/verified against {settings.DATABASE_URL}")

    with session_scope() as db:
        existing = db.scalar(select(AdminUser).limit(1))
        if existing:
            print("Admin user already exists — skipping bootstrap.")
            return
        if not settings.BOOTSTRAP_ADMIN_PASSWORD_HASH:
            print(
                "No admin user exists yet, and BOOTSTRAP_ADMIN_PASSWORD_HASH is unset.\n"
                "Run scripts/gen_secrets.py, put the output in .env, then re-run this script.",
                file=sys.stderr,
            )
            sys.exit(1)
        db.add(AdminUser(
            username=settings.BOOTSTRAP_ADMIN_USERNAME,
            password_hash=settings.BOOTSTRAP_ADMIN_PASSWORD_HASH,
            role="owner",
        ))
        print(f"Created bootstrap admin user '{settings.BOOTSTRAP_ADMIN_USERNAME}'.")


if __name__ == "__main__":
    main()
