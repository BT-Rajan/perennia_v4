from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_admin, require_csrf
from app.models import AdminUser

router = APIRouter(prefix="/admin/api/services", tags=["admin-services"], dependencies=[Depends(require_csrf)])


# ── Schemas ──────────────────────────────────────────────────────────

class QuestionOut(BaseModel):
    id: str
    kind: str
    label: str
    required: bool
    position: int


class ServiceOut(BaseModel):
    id: str
    name: str
    slug: str
    duration_minutes: int
    buffer_before_minutes: int
    buffer_after_minutes: int
    requires_confirmation: bool
    payment_required: bool
    location_type: str
    is_active: bool
    position: int
    translations: dict[str, dict[str, str]]
    questions: list[QuestionOut] = []


class ServiceCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=64)
    duration_minutes: int = Field(ge=5, le=480)
    buffer_before_minutes: int = Field(default=0, ge=0, le=120)
    buffer_after_minutes: int = Field(default=0, ge=0, le=120)
    requires_confirmation: bool = False
    payment_required: bool = False
    location_type: str = "in_person"
    is_active: bool = True
    position: int = 0
    translations: dict[str, dict[str, str]] = Field(default_factory=dict)


class ServiceUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=64)
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    buffer_before_minutes: int | None = Field(default=None, ge=0, le=120)
    buffer_after_minutes: int | None = Field(default=None, ge=0, le=120)
    requires_confirmation: bool | None = None
    payment_required: bool | None = None
    location_type: str | None = None
    is_active: bool | None = None
    position: int | None = None
    translations: dict[str, dict[str, str]] | None = None


class QuestionCreateIn(BaseModel):
    kind: str
    label: str = Field(min_length=1, max_length=200)
    required: bool = False
    position: int = 0


class QuestionUpdateIn(BaseModel):
    kind: str | None = None
    label: str | None = Field(default=None, min_length=1, max_length=200)
    required: bool | None = None
    position: int | None = None


class QuestionReorderIn(BaseModel):
    ordered_ids: list[str]


def _service_dict(s) -> dict[str, Any]:
    return dict(
        id=s.id, name=s.name, slug=s.slug, duration_minutes=s.duration_minutes,
        buffer_before_minutes=s.buffer_before_minutes, buffer_after_minutes=s.buffer_after_minutes,
        requires_confirmation=s.requires_confirmation, payment_required=s.payment_required,
        location_type=s.location_type, is_active=s.is_active, position=s.position,
        translations=s.translations,
        questions=[
            QuestionOut(id=q.id, kind=q.kind, label=q.label, required=q.required, position=q.position)
            for q in s.questions
        ],
    )


# ── Services ─────────────────────────────────────────────────────────

@router.get("", response_model=list[ServiceOut])
def list_services(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import services_service
    return [ServiceOut(**_service_dict(s)) for s in services_service.list_services(db, active_only=False)]


@router.post("", response_model=ServiceOut)
def create_service(body: ServiceCreateIn, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import services_service
    try:
        service = services_service.create_service(
            db, name=body.name, slug=body.slug, duration_minutes=body.duration_minutes,
            buffer_before_minutes=body.buffer_before_minutes, buffer_after_minutes=body.buffer_after_minutes,
            requires_confirmation=body.requires_confirmation, payment_required=body.payment_required,
            location_type=body.location_type, is_active=body.is_active, position=body.position,
            translations=body.translations, actor_id=admin.id, actor_username=admin.username,
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.refresh(service)
    return ServiceOut(**_service_dict(service))


@router.get("/{service_id}", response_model=ServiceOut)
def get_service(service_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import services_service
    service = services_service.get_service(db, service_id)
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No service {service_id!r}")
    return ServiceOut(**_service_dict(service))


@router.patch("/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: str, body: ServiceUpdateIn,
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    from app import services_service
    try:
        service = services_service.update_service(
            db, service_id, name=body.name, slug=body.slug, duration_minutes=body.duration_minutes,
            buffer_before_minutes=body.buffer_before_minutes, buffer_after_minutes=body.buffer_after_minutes,
            requires_confirmation=body.requires_confirmation, payment_required=body.payment_required,
            location_type=body.location_type, is_active=body.is_active, position=body.position,
            translations=body.translations, actor_id=admin.id, actor_username=admin.username,
        )
        db.commit()
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.refresh(service)
    return ServiceOut(**_service_dict(service))


@router.delete("/{service_id}")
def delete_service(service_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Soft delete (deactivate) — see services_service.delete_service."""
    from app import services_service
    ok = services_service.delete_service(db, service_id, actor_id=admin.id, actor_username=admin.username)
    db.commit()
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No service {service_id!r}")
    return {"ok": True}


# ── Custom questions ─────────────────────────────────────────────────

@router.post("/{service_id}/questions", response_model=QuestionOut)
def add_question(
    service_id: str, body: QuestionCreateIn,
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    from app import services_service
    try:
        q = services_service.add_question(
            db, service_id, kind=body.kind, label=body.label, required=body.required,
            position=body.position, actor_id=admin.id, actor_username=admin.username,
        )
        db.commit()
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.refresh(q)
    return QuestionOut(id=q.id, kind=q.kind, label=q.label, required=q.required, position=q.position)


@router.patch("/{service_id}/questions/{question_id}", response_model=QuestionOut)
def update_question(
    service_id: str, question_id: str, body: QuestionUpdateIn,
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    from app import services_service
    try:
        q = services_service.update_question(
            db, service_id, question_id, kind=body.kind, label=body.label, required=body.required,
            position=body.position, actor_id=admin.id, actor_username=admin.username,
        )
        db.commit()
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.refresh(q)
    return QuestionOut(id=q.id, kind=q.kind, label=q.label, required=q.required, position=q.position)


@router.delete("/{service_id}/questions/{question_id}")
def delete_question(
    service_id: str, question_id: str,
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    from app import services_service
    ok = services_service.delete_question(db, service_id, question_id, actor_id=admin.id, actor_username=admin.username)
    db.commit()
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No question {question_id!r}")
    return {"ok": True}


@router.post("/{service_id}/questions/reorder")
def reorder_questions(
    service_id: str, body: QuestionReorderIn,
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    from app import services_service
    try:
        services_service.reorder_questions(
            db, service_id, body.ordered_ids, actor_id=admin.id, actor_username=admin.username
        )
        db.commit()
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return {"ok": True}
