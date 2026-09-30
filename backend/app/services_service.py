"""
Read/write access to bookable Services and their per-service custom
intake questions. Mirrors content_service.py's role for content pages:
routers never touch the ORM directly, so validation and audit logging
happen in exactly one place.

Pass 0 of docs/CALENDAR_MODULE_PLAN.md — the admin-managed Service
catalog exists as its own resource here, but the public booking flow
(app/booking_service.py) is not yet wired to it. That's the next slice
of Pass 8, once this admin surface is in place and stable.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Service, ServiceCustomQuestion

QUESTION_KINDS = {"text", "textarea", "number", "bool", "phone"}
LOCATION_TYPES = {"in_person", "phone", "link_provided"}

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    slug = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return slug or "service"


def _unique_slug(db: Session, base: str, *, exclude_id: str | None = None) -> str:
    """Appends -2, -3, ... on collision rather than erroring — an admin
    naming two services "Consultation" (e.g. one archived, one new)
    shouldn't have to hand-pick a slug just to save."""
    slug = base
    n = 2
    while True:
        existing = db.scalar(select(Service).where(Service.slug == slug))
        if existing is None or existing.id == exclude_id:
            return slug
        slug = f"{base}-{n}"
        n += 1


def _validate_service_fields(*, duration_minutes: int, buffer_before_minutes: int,
                              buffer_after_minutes: int, location_type: str) -> None:
    if not (5 <= duration_minutes <= 480):
        raise ValueError("duration_minutes must be between 5 and 480")
    if not (0 <= buffer_before_minutes <= 120):
        raise ValueError("buffer_before_minutes must be between 0 and 120")
    if not (0 <= buffer_after_minutes <= 120):
        raise ValueError("buffer_after_minutes must be between 0 and 120")
    if location_type not in LOCATION_TYPES:
        raise ValueError(f"location_type must be one of {sorted(LOCATION_TYPES)}")


# ── Services ─────────────────────────────────────────────────────────

def list_services(db: Session, *, active_only: bool) -> list[Service]:
    stmt = select(Service).order_by(Service.position, Service.name)
    if active_only:
        stmt = stmt.where(Service.is_active.is_(True))
    return list(db.scalars(stmt))


def get_service(db: Session, service_id: str) -> Service | None:
    return db.get(Service, service_id)


def create_service(
    db: Session, *, name: str, duration_minutes: int, slug: str | None = None,
    buffer_before_minutes: int = 0, buffer_after_minutes: int = 0,
    requires_confirmation: bool = False, payment_required: bool = False,
    location_type: str = "in_person", is_active: bool = True, position: int = 0,
    translations: dict | None = None, actor_id: str | None, actor_username: str | None,
) -> Service:
    name = name.strip()
    if not name:
        raise ValueError("name is required")
    _validate_service_fields(
        duration_minutes=duration_minutes, buffer_before_minutes=buffer_before_minutes,
        buffer_after_minutes=buffer_after_minutes, location_type=location_type,
    )

    final_slug = _unique_slug(db, slugify(slug or name))

    service = Service(
        name=name, slug=final_slug, duration_minutes=duration_minutes,
        buffer_before_minutes=buffer_before_minutes, buffer_after_minutes=buffer_after_minutes,
        requires_confirmation=requires_confirmation, payment_required=payment_required,
        location_type=location_type, is_active=is_active, position=position,
        translations=translations or {}, updated_by=actor_id,
    )
    db.add(service)
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username, action="service.create"))
    db.flush()  # populate service.id for the response
    return service


def update_service(
    db: Session, service_id: str, *, name: str | None = None, slug: str | None = None,
    duration_minutes: int | None = None, buffer_before_minutes: int | None = None,
    buffer_after_minutes: int | None = None, requires_confirmation: bool | None = None,
    payment_required: bool | None = None, location_type: str | None = None,
    is_active: bool | None = None, position: int | None = None, translations: dict | None = None,
    actor_id: str | None, actor_username: str | None,
) -> Service:
    service = db.get(Service, service_id)
    if service is None:
        raise KeyError(f"No service {service_id!r}")

    _validate_service_fields(
        duration_minutes=duration_minutes if duration_minutes is not None else service.duration_minutes,
        buffer_before_minutes=(
            buffer_before_minutes if buffer_before_minutes is not None else service.buffer_before_minutes
        ),
        buffer_after_minutes=(
            buffer_after_minutes if buffer_after_minutes is not None else service.buffer_after_minutes
        ),
        location_type=location_type if location_type is not None else service.location_type,
    )

    if name is not None:
        name = name.strip()
        if not name:
            raise ValueError("name cannot be blank")
        service.name = name
    if slug is not None:
        service.slug = _unique_slug(db, slugify(slug), exclude_id=service.id)
    if duration_minutes is not None:
        service.duration_minutes = duration_minutes
    if buffer_before_minutes is not None:
        service.buffer_before_minutes = buffer_before_minutes
    if buffer_after_minutes is not None:
        service.buffer_after_minutes = buffer_after_minutes
    if requires_confirmation is not None:
        service.requires_confirmation = requires_confirmation
    if payment_required is not None:
        service.payment_required = payment_required
    if location_type is not None:
        service.location_type = location_type
    if is_active is not None:
        service.is_active = is_active
    if position is not None:
        service.position = position
    if translations is not None:
        service.translations = translations
    service.updated_by = actor_id

    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username, action="service.update", target=service_id))
    return service


def delete_service(db: Session, service_id: str, *, actor_id: str | None, actor_username: str | None) -> bool:
    """Soft delete only. A hard delete becomes unsafe the moment
    Appointment gains a service_id FK (next slice of Pass 8) — rather
    than adding that guard later, this endpoint is deactivate-only from
    the start so no client ever has to be migrated off a hard-delete
    call. Deactivating removes a service from public listings; the row
    and its question history stay intact."""
    service = db.get(Service, service_id)
    if service is None:
        return False
    service.is_active = False
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username, action="service.deactivate", target=service_id))
    return True


# ── Custom questions ─────────────────────────────────────────────────

def add_question(
    db: Session, service_id: str, *, kind: str, label: str, required: bool = False,
    position: int = 0, actor_id: str | None, actor_username: str | None,
) -> ServiceCustomQuestion:
    service = db.get(Service, service_id)
    if service is None:
        raise KeyError(f"No service {service_id!r}")
    if kind not in QUESTION_KINDS:
        raise ValueError(f"kind must be one of {sorted(QUESTION_KINDS)}")
    label = label.strip()
    if not label:
        raise ValueError("label is required")

    question = ServiceCustomQuestion(
        service_id=service_id, kind=kind, label=label, required=required, position=position
    )
    db.add(question)
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username,
                     action="service.question.create", target=service_id))
    db.flush()
    return question


def update_question(
    db: Session, service_id: str, question_id: str, *, kind: str | None = None,
    label: str | None = None, required: bool | None = None, position: int | None = None,
    actor_id: str | None, actor_username: str | None,
) -> ServiceCustomQuestion:
    question = db.get(ServiceCustomQuestion, question_id)
    if question is None or question.service_id != service_id:
        raise KeyError(f"No question {question_id!r} for service {service_id!r}")

    if kind is not None:
        if kind not in QUESTION_KINDS:
            raise ValueError(f"kind must be one of {sorted(QUESTION_KINDS)}")
        question.kind = kind
    if label is not None:
        label = label.strip()
        if not label:
            raise ValueError("label cannot be blank")
        question.label = label
    if required is not None:
        question.required = required
    if position is not None:
        question.position = position

    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username,
                     action="service.question.update", target=question_id))
    return question


def delete_question(
    db: Session, service_id: str, question_id: str, *, actor_id: str | None, actor_username: str | None
) -> bool:
    question = db.get(ServiceCustomQuestion, question_id)
    if question is None or question.service_id != service_id:
        return False
    db.delete(question)
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username,
                     action="service.question.delete", target=question_id))
    return True


def reorder_questions(
    db: Session, service_id: str, ordered_ids: list[str], *, actor_id: str | None, actor_username: str | None
) -> None:
    questions = {
        q.id: q for q in db.scalars(
            select(ServiceCustomQuestion).where(ServiceCustomQuestion.service_id == service_id)
        )
    }
    missing = set(ordered_ids) - set(questions)
    if missing:
        raise KeyError(f"Unknown question id(s) for service {service_id!r}: {sorted(missing)}")
    for idx, qid in enumerate(ordered_ids):
        questions[qid].position = idx
    db.add(AuditLog(actor_id=actor_id, actor_username=actor_username,
                     action="service.question.reorder", target=service_id))
