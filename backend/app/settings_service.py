"""
Read/write access to configurable settings. Every value the site ever
shows — to a visitor or an admin — should be reached through
`get_setting`/`get_all_public`, never a hardcoded literal in a component
or route. A DB row is only written once an admin actually changes a
value from its default (sparse storage — an empty table is a fully
valid, fully-defaulted site).

Caching: REGISTRY has 70 settings. Reading them individually (the
original implementation of get_setting: one `db.get(SiteSetting, key)`
per key) means /api/config/public alone issues 70 separate queries,
and building a chat reply or a booking-availability response does the
same thing 7-9 times over for the handful of settings each needs. All
of that is read traffic against a table that's only ever written from
the admin settings screen, so it's cached in-process after the first
read of any setting and invalidated on any write. Safe across the
threadpool FastAPI runs these (sync) handlers in — guarded by a lock
whose hold time is a dict copy, not a query.
"""
from __future__ import annotations

import json
import threading
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, SiteSetting
from app.security import decrypt_secret, encrypt_secret
from app.settings_registry import REGISTRY, SettingDef, get_def

_cache_lock = threading.Lock()
# key -> (raw_value, is_secret). None means "not loaded yet" — distinct
# from an empty dict, which is a legitimate "no settings customized yet"
# state (sparse storage, see module docstring).
_cache: dict[str, tuple[str, bool]] | None = None


def _row_cache(db: Session) -> dict[str, tuple[str, bool]]:
    global _cache
    with _cache_lock:
        if _cache is None:
            rows = db.execute(select(SiteSetting)).scalars().all()
            _cache = {r.key: (r.value, r.is_secret) for r in rows}
        return _cache


def invalidate_cache() -> None:
    """Called by every write path below. Next read repopulates from the
    DB with one query, same as a cold-start cache miss."""
    global _cache
    with _cache_lock:
        _cache = None


def _decode(d: SettingDef, raw: str) -> Any:
    return json.loads(raw)


def _encode(value: Any) -> str:
    return json.dumps(value)


def get_setting(db: Session, key: str) -> Any:
    d = get_def(key)
    entry = _row_cache(db).get(key)
    if entry is None:
        return d.default
    raw_value, is_secret = entry
    raw = decrypt_secret(raw_value) if is_secret else raw_value
    stored = _decode(d, raw)
    if d.i18n and isinstance(d.default, dict) and isinstance(stored, dict):
        # Merge so a language an admin hasn't translated yet still falls
        # back to the default rather than disappearing from the response.
        merged = dict(d.default)
        merged.update(stored)
        return merged
    return stored


def get_category(db: Session, category: str) -> dict[str, Any]:
    """Never decrypts secret-typed settings — a masked placeholder is
    returned instead (see _secret_placeholder), the same rule
    get_all_settings applies. This function backs the admin settings
    UI's edit forms, so a plaintext API key must never transit this
    path even to an authenticated admin: it shouldn't sit in a browser
    network log, get bound into a visible input value, or round-trip
    back on save (the UI leaves a secret field untouched to keep it).

    Reads go through the process-wide settings cache (see module
    docstring), so a category with 10 settings costs zero extra
    queries beyond whatever already primed the cache this process."""
    from app.settings_registry import defs_for_category
    out = {}
    for d in defs_for_category(category):
        if d.secret:
            out[d.key] = _secret_placeholder(db, d.key)
        else:
            out[d.key] = get_setting(db, d.key)
    return out


SECRET_PLACEHOLDER = "••••••••"


def _secret_placeholder(db: Session, key: str) -> str:
    """Decrypts only to check whether a real (non-empty) value is
    stored — the decrypted value itself is never returned. This is
    what distinguishes "never configured" (empty row or no row) from
    "configured" (masked placeholder) without leaking the secret."""
    entry = _row_cache(db).get(key)
    if entry is None:
        return ""
    raw_value, _is_secret = entry
    try:
        value = _decode(get_def(key), decrypt_secret(raw_value))
    except ValueError:
        return ""
    return SECRET_PLACEHOLDER if value else ""


def get_all(db: Session, *, include_secrets: bool) -> dict[str, Any]:
    """include_secrets=False is what powers the PUBLIC config API — a
    secret-typed setting is simply omitted, never masked-and-included,
    so there's no risk of a masking bug leaking a fragment.

    Reads go through the process-wide settings cache (see module
    docstring) rather than one db.get() per registry key — this was
    the single hottest N+1 in the app, since every visitor's page load
    hits /api/config/public and it only carries a 30s cache header."""
    out: dict[str, Any] = {}
    for key, d in REGISTRY.items():
        if d.secret and not include_secrets:
            continue
        out[key] = get_setting(db, key)
    return out


def all_secret_placeholders(db: Session) -> dict[str, str]:
    """Masked values for every secret-typed setting — used by the admin
    full-settings export. Backed by the same process-wide cache as
    every other read here, so this costs no additional queries beyond
    whatever already primed the cache."""
    secret_defs = [d for d in REGISTRY.values() if d.secret]
    return {d.key: _secret_placeholder(db, d.key) for d in secret_defs}


def set_setting(db: Session, key: str, value: Any, *, actor_id: str | None, actor_username: str | None,
                 ip_address: str | None = None) -> None:
    d = get_def(key)

    # Defense in depth: the settings UI's edit form is populated from
    # get_category(), which returns this exact placeholder for a
    # secret that's already set (see _secret_placeholder) rather than
    # the real value — precisely so a naive "submit the whole form"
    # save can never round-trip a masked display string back in as
    # the new value and destroy the real secret. If it ever does slip
    # through, treat it as "no change" rather than overwriting.
    if d.secret and value == SECRET_PLACEHOLDER:
        return

    d.validate(value)
    raw = _encode(value)
    stored = encrypt_secret(raw) if d.secret else raw

    row = db.get(SiteSetting, key)
    if row is None:
        row = SiteSetting(key=key, value=stored, is_secret=d.secret)
        db.add(row)
    else:
        row.value = stored
        row.is_secret = d.secret
    row.updated_by = actor_id

    db.add(AuditLog(
        actor_id=actor_id,
        actor_username=actor_username,
        action="setting.update",
        target=key,
        detail="<redacted secret value>" if d.secret else raw[:500],
        ip_address=ip_address,
    ))

    # autoflush is off (see app/db.py), so without this a get_setting()
    # call later in the same request/session wouldn't see this write
    # once invalidate_cache() below forces it to re-query.
    db.flush()
    invalidate_cache()


def set_many(db: Session, values: dict[str, Any], *, actor_id: str | None, actor_username: str | None,
             ip_address: str | None = None) -> list[str]:
    """Validates every key BEFORE writing any of them, so a bulk save
    from the admin panel is all-or-nothing rather than leaving settings
    half-updated on a validation error partway through."""
    unknown = [k for k in values if k not in REGISTRY]
    if unknown:
        raise KeyError(f"Unknown setting keys: {unknown}")
    for key, value in values.items():
        get_def(key).validate(value)

    for key, value in values.items():
        set_setting(db, key, value, actor_id=actor_id, actor_username=actor_username, ip_address=ip_address)
    return list(values.keys())
