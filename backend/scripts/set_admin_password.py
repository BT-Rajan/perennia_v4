#!/usr/bin/env python3
"""
Sets (resets) an admin dashboard password from the command line, for
when the password is lost or the first-install one was never noted.
Signs that user out everywhere (their existing sessions are deleted).

    cd backend && venv/bin/python scripts/set_admin_password.py            # user "admin", prompts
    cd backend && venv/bin/python scripts/set_admin_password.py --username someone
    ADMIN_PASSWORD='...' venv/bin/python scripts/set_admin_password.py      # non-interactive

The password is read from the ADMIN_PASSWORD environment variable or a
hidden prompt — never from the command line, so it doesn't land in
shell history or `ps`. Also reactivates the account if it was disabled.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select

from app.db import session_scope
from app.models import AdminSession, AdminUser
from app.security import hash_password

MIN_LENGTH = 10


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--username", default="admin", help='admin username (default "admin")')
    args = parser.parse_args()

    with session_scope() as db:
        user = db.scalar(select(AdminUser).where(AdminUser.username == args.username))
        if not user:
            names = ", ".join(db.scalars(select(AdminUser.username)).all()) or "none"
            sys.exit(f"No admin user '{args.username}'. Existing admin users: {names}")

        password = os.environ.get("ADMIN_PASSWORD") or ""
        if not password:
            password = getpass.getpass(f"New password for '{args.username}': ")
            if password != getpass.getpass("Repeat it: "):
                sys.exit("Passwords don't match — nothing changed.")
        if len(password) < MIN_LENGTH:
            sys.exit(f"Password must be at least {MIN_LENGTH} characters — nothing changed.")

        user.password_hash = hash_password(password)
        user.is_active = True
        db.execute(delete(AdminSession).where(AdminSession.user_id == user.id))

    print(f"Password updated for '{args.username}'. Sign in again at /admin.")


if __name__ == "__main__":
    main()
