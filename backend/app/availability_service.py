"""
Read/write access to AvailabilityRule, and resolution of "what hours is
a given service/date actually open" from those rules. See
docs/CALENDAR_MODULE_PLAN.md (Pass 9) and models.py::AvailabilityRule
for the precedence this implements. booking_service.py is the only
caller of effective_ranges(); everything else here is admin CRUD
following the same routers-never-touch-the-ORM split as
content_service.py / services_service.py.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, AvailabilityRule, Service

KINDS = {"weekly", "date_override"}


def _time_to_minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _validate_time_range(start_time: str | None, end_time: str | None, *, is_closed: bool) -> None:
    if is_closed:
        return
    if not start_time or not end_time:
        raise ValueError("start_time and end_time are required unless is_closed is set")
    try:
        start_min, end_min = _time_to_minutes(start_time), _time_to_minutes(end_time)
    except (ValueError, IndexError):
        raise ValueError("start_time/end_time must be HH:MM") from None
    if end_min <= start_min:
        raise ValueError("end_time must be after start_time")


def _validate_rule_shape(*, kind: str, weekday: int | None, date: str | None) -> None:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {sorted(KINDS)}")
    if kind == "weekly":
        if weekday is None or not (0 <= weekday <= 6):
            raise ValueError("weekly rules require weekday in 0..6")
        if date is not None:
            raise ValueError("weekly rules must not set date")
    else:  # date_override
        if date is None:
            raise ValueError("date_override rules require date")
        try:
            dt.date.fromisoformat(date)
        except ValueError:
            raise ValueError("date must be YYYY-MM-DD") from None
        if weekday is not None:
            raise ValueError("date_override rules must not set weekday")


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and a_end > b_start


def _check_weekly_overlap(
    db: Session, *, service_id: str | None, weekday: int, start_time: str, end_time: str,
    exclude_id: str | None = None,
) -> None:
    """Two weekly rules with overlapping time ranges for the same
    (service_id, weekday) would make "what's open" ambiguous, so this
    is rejected at write time rather than left for effective_ranges to
    somehow reconcile. Split-day hours (e.g. 09:00-12:00 and
    13:00-17:00) are fine — they simply don't overlap."""
    start_min, end_min = _time_to_minutes(start_time), _time_to_minutes(end_time)
    stmt = select(AvailabilityRule).where(
        AvailabilityRule.kind == "weekly", AvailabilityRule.service_id == service_id,
        AvailabilityRule.weekday == weekday, AvailabilityRule.is_closed.is_(False),
    )
    for existing in db.scalars(stmt):
        if existing.id == exclude_id:
            continue
        e_start, e_end = _time_to_minutes(existing.start_time), _time_to_minutes(existing.end_time)
        if _overlaps(start_min, end_min, e_start, e_end):
            raise ValueError(f"Overlaps existing rule {existing.id!r} ({existing.start_time}-{existing.end_time})")


# ── CRUD ─────────────────────────────────────────────────────────────

def list_rules(db: Session, *, service_id: str | None) -> list[AvailabilityRule]:
    stmt = (
        select(AvailabilityRule)
        .where(AvailabilityRule.service_id == service_id)
        .order_by(AvailabilityRule.kind, AvailabilityRule.weekday, AvailabilityRule.date)
    )
    return list(db.scalars(stmt))


def create_rule(
    db: Session, *, service_id: str | None = None, kind: str, weekday: int | None = None,
    date: str | None = None, start_time: str | None = None, end_time: str | None = None,
    is_closed: bool = False, actor_id: str | None, actor_username: str | None,
) -> AvailabilityRule:
    if service_id is not None and db.get(Service, service_id) is None:
        raise KeyError(f"No service {service_id!r}")
    _validate_rule_shape(kind=kind, weekday=weekday, date=date)
    _validate_time_range(start_time, end_time, is_closed=is_closed)
    if kind == "weekly" and not is_closed:
        _check_weekly_overlap(db, service_id=service_id, weekday=weekday, start_time=start_time, end_time=end_time)

    rule = AvailabilityRule(
        service_id=service_id, kind=kind, weekday=weekday, date=date,
        start_time=None if is_closed else start_time, end_time=None if is_closed else end_time,
        is_closed=is_closed,
    )
    db.add(rule)
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username, action="availability_rule.create"))
    db.flush()  # populate rule.id for the response
    return rule


def update_rule(
    db: Session, rule_id: str, *, weekday: int | None = None, date: str | None = None,
    start_time: str | None = None, end_time: str | None = None, is_closed: bool | None = None,
    actor_id: str | None, actor_username: str | None,
) -> AvailabilityRule:
    rule = db.get(AvailabilityRule, rule_id)
    if rule is None:
        raise KeyError(f"No availability rule {rule_id!r}")

    # kind, and which of weekday/date applies, never change after
    # creation — that's a different rule, not an edit of this one.
    new_weekday = weekday if weekday is not None else rule.weekday
    new_date = date if date is not None else rule.date
    new_is_closed = is_closed if is_closed is not None else rule.is_closed
    new_start = start_time if start_time is not None else rule.start_time
    new_end = end_time if end_time is not None else rule.end_time

    _validate_rule_shape(kind=rule.kind, weekday=new_weekday, date=new_date)
    _validate_time_range(new_start, new_end, is_closed=new_is_closed)
    if rule.kind == "weekly" and not new_is_closed:
        _check_weekly_overlap(
            db, service_id=rule.service_id, weekday=new_weekday,
            start_time=new_start, end_time=new_end, exclude_id=rule.id,
        )

    rule.weekday, rule.date, rule.is_closed = new_weekday, new_date, new_is_closed
    rule.start_time = None if new_is_closed else new_start
    rule.end_time = None if new_is_closed else new_end

    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username,
                     action="availability_rule.update", target=rule_id))
    return rule


def delete_rule(db: Session, rule_id: str, *, actor_id: str | None, actor_username: str | None) -> bool:
    rule = db.get(AvailabilityRule, rule_id)
    if rule is None:
        return False
    db.delete(rule)
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username,
                     action="availability_rule.delete", target=rule_id))
    return True


# ── Resolution ───────────────────────────────────────────────────────

def any_rules_exist(db: Session) -> bool:
    return db.scalar(select(func.count()).select_from(AvailabilityRule)) > 0


def effective_ranges(
    db: Session, *, service_id: str | None, weekday: int, date_str: str
) -> list[tuple[int, int]] | None:
    """Resolved open ranges (start_minutes, end_minutes) for one
    service on one date, most-specific-wins: service+date override >
    business-wide date override > service weekly > business-wide
    weekly.

    Returns **None** (not []) if literally no AvailabilityRule exists
    anywhere yet — the caller (booking_service.py) falls back to the
    legacy booking.* settings in that case, so a site that hasn't
    touched this feature keeps behaving exactly as before this pass.
    Returns **[]** (closed, not "please fall back") once at least one
    rule exists somewhere but nothing resolves for this particular
    service/date — that's a real, intentional "closed," not a missing
    migration."""
    if not any_rules_exist(db):
        return None

    def _date_override(sid: str | None) -> list[AvailabilityRule]:
        stmt = select(AvailabilityRule).where(
            AvailabilityRule.kind == "date_override", AvailabilityRule.service_id == sid,
            AvailabilityRule.date == date_str,
        )
        return list(db.scalars(stmt))

    def _weekly(sid: str | None) -> list[AvailabilityRule]:
        stmt = select(AvailabilityRule).where(
            AvailabilityRule.kind == "weekly", AvailabilityRule.service_id == sid,
            AvailabilityRule.weekday == weekday,
        )
        return list(db.scalars(stmt))

    lookups = []
    if service_id is not None:
        lookups.append(lambda: _date_override(service_id))
    lookups.append(lambda: _date_override(None))
    if service_id is not None:
        lookups.append(lambda: _weekly(service_id))
    lookups.append(lambda: _weekly(None))

    for lookup in lookups:
        rows = lookup()
        if not rows:
            continue
        if any(r.is_closed for r in rows):
            return []
        return [(_time_to_minutes(r.start_time), _time_to_minutes(r.end_time)) for r in rows]

    return []  # rules exist elsewhere, but nothing matches this service/date -> closed
