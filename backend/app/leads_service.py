"""
Lead capture and management. Leads are never created via a dedicated
"submit a lead" form — they're captured automatically from real
signals (a booking, an email address volunteered in chat), and
upserted by email so the same person touching the business twice
consolidates into one record instead of duplicating.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lead

VALID_STATUSES = ("new", "contacted", "qualified", "converted", "lost")


def _utcnow_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def capture_lead(
    db: Session, *, email: str, source: str, name: str = "", phone: str = "",
    transcript_entry: dict | None = None,
) -> tuple[Lead, bool]:
    """Finds an existing lead by email (case-insensitive) and appends
    to it, or creates a new one. Never downgrades known info — an
    empty `name`/`phone` on a later touch doesn't erase a name/phone
    already on file. Returns (lead, created) so callers can decide
    whether a *new* lead is alert-worthy without re-querying."""
    email_norm = email.strip().lower()
    existing = db.scalar(select(Lead).where(Lead.email == email_norm))
    created = existing is None

    if existing is None:
        lead = Lead(email=email_norm, name=name.strip(), phone=phone.strip(), source=source)
        db.add(lead)
    else:
        lead = existing
        if name.strip():
            lead.name = name.strip()
        if phone.strip():
            lead.phone = phone.strip()

    if transcript_entry is not None:
        lead.transcript = [*(lead.transcript or []), {**transcript_entry, "at": _utcnow_iso()}]

    db.flush()
    return lead, created


def create_lead(
    db: Session, *, name: str, email: str, phone: str = "", notes: str = "", status: str = "new",
) -> Lead:
    """Manual entry point for the admin 'Add lead' button — everywhere
    else a Lead is created via capture_lead's auto-upsert-by-email
    (booking/chat signals), but an admin adding one directly should
    still land in the same table with the same shape, not a separate
    path. Reuses capture_lead's upsert-by-email so pasting in an email
    that already has a lead record merges into it instead of duplicating.
    """
    email_norm = email.strip().lower()
    if not email_norm:
        raise ValueError("email is required")
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of {VALID_STATUSES}")
    lead, _created = capture_lead(db, email=email_norm, source="manual", name=name, phone=phone)
    if notes.strip():
        lead.notes = notes.strip()
    lead.status = status
    db.flush()
    return lead


def list_leads(db: Session, *, status: str | None = None, source: str | None = None) -> list[Lead]:
    stmt = select(Lead).order_by(Lead.created_at.desc())
    if status:
        stmt = stmt.where(Lead.status == status)
    if source:
        stmt = stmt.where(Lead.source == source)
    return list(db.scalars(stmt))


def get_lead(db: Session, lead_id: str) -> Lead | None:
    return db.get(Lead, lead_id)


def update_lead(db: Session, lead_id: str, *, status: str | None = None, notes: str | None = None) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise KeyError(f"No lead {lead_id!r}")
    if status is not None:
        if status not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        lead.status = status
    if notes is not None:
        lead.notes = notes
    return lead


def delete_lead(db: Session, lead_id: str) -> bool:
    lead = db.get(Lead, lead_id)
    if lead is None:
        return False
    db.delete(lead)
    return True
