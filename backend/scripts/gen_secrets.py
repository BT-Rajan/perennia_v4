#!/usr/bin/env python3
"""
Generates the secrets .env needs. Run once per environment (dev, staging,
prod each get their own — never share a SECRET_KEY or ENCRYPTION_KEY
across environments, and never commit the output).

    python scripts/gen_secrets.py
    python scripts/gen_secrets.py --password "correct horse battery staple"
    python scripts/gen_secrets.py --password "..." --write-env .env
"""
from __future__ import annotations

import argparse
import getpass
import re
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cryptography.fernet import Fernet
from passlib.context import CryptContext

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _set_env_var(content: str, key: str, value: str) -> str:
    """Replaces KEY=... if present (anywhere on its own line), else
    appends it. Used instead of a shell/PowerShell text-patching step
    in the installer scripts — doing this in Python avoids a whole
    class of quoting bugs with special characters (&, %, !, quotes)
    that a generated secret or password could otherwise contain."""
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    line = f"{key}={value}"
    if pattern.search(content):
        return pattern.sub(line, content, count=1)
    sep = "" if content.endswith("\n") or not content else "\n"
    return content + sep + line + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", help="Admin password to hash (prompts securely if omitted)")
    parser.add_argument("--username", default="admin", help="Bootstrap admin username")
    parser.add_argument("--write-env", metavar="PATH",
                         help="Write SECRET_KEY/ENCRYPTION_KEY/BOOTSTRAP_ADMIN_* directly into this "
                              "existing .env file instead of printing them to stdout — used by the "
                              "installer scripts so no secret ever needs to round-trip through shell "
                              "text-parsing.")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Admin password to hash: ")
    if len(password) < 12:
        print("WARNING: password is shorter than 12 characters — consider something longer.", file=sys.stderr)

    values = {
        "SECRET_KEY": secrets.token_urlsafe(48),
        "ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "BOOTSTRAP_ADMIN_USERNAME": args.username,
        "BOOTSTRAP_ADMIN_PASSWORD_HASH": _pwd_ctx.hash(password),
    }

    if args.write_env:
        env_path = Path(args.write_env)
        if not env_path.exists():
            print(f"FATAL: {env_path} does not exist — copy .env.example first.", file=sys.stderr)
            sys.exit(1)
        content = env_path.read_text()
        for key, value in values.items():
            content = _set_env_var(content, key, value)
        env_path.write_text(content)
        print(f"Secrets written to {env_path}")
    else:
        print("# Paste these into your .env — generated fresh, never reuse across environments.\n")
        for key, value in values.items():
            print(f"{key}={value}")


if __name__ == "__main__":
    main()
