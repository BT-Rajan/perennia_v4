#!/usr/bin/env python3
"""
Creates (or resets) the admin dashboard account so you can always log in.

Defaults:  username = admin     password = Admin#99

    cd backend && venv/bin/python scripts/reset_admin.py
    cd backend && venv/bin/python scripts/reset_admin.py --username admin --password 'Other#Pass1'
    ADMIN_USERNAME=boss ADMIN_PASSWORD='...' venv/bin/python scripts/reset_admin.py

What it does (idempotent — safe to run any number of times):
  * makes sure all tables exist,
  * creates the user if it doesn't exist (role "owner"), otherwise
    updates its password,
  * re-activates the account if it was disabled,
  * deletes the user's existing sessions (signs them out everywhere).

Unlike set_admin_password.py this does NOT require the user to exist
already and does NOT enforce a minimum password length, so it works on a
fresh/broken install. Change the password to something stronger from the
admin panel once you are in.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select

from app.db import Base, engine, session_scope
from app.models import AdminSession, AdminUser
from app.security import hash_password, verify_password

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "Admin#99"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or reset the admin account.")
    parser.add_argument("--username", default=os.environ.get("ADMIN_USERNAME", DEFAULT_USERNAME))
    parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD", DEFAULT_PASSWORD))
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)

    with session_scope() as db:
        user = db.scalar(select(AdminUser).where(AdminUser.username == args.username))
        if user is None:
            user = AdminUser(
                username=args.username,
                password_hash=hash_password(args.password),
                role="owner",
                is_active=True,
            )
            db.add(user)
            db.flush()
            action = "Created"
        else:
            user.password_hash = hash_password(args.password)
            user.is_active = True
            db.execute(delete(AdminSession).where(AdminSession.user_id == user.id))
            action = "Reset"

        # Verify what we just stored actually authenticates.
        if not verify_password(args.password, user.password_hash):
            sys.exit("Internal error: stored hash does not verify — nothing committed.")

    print(f"{action} admin user '{args.username}' (password set). Sign in at /admin.")


if __name__ == "__main__":
    main()
