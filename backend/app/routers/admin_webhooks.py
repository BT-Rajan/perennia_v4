from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_admin, require_csrf
from app.models import AdminUser

router = APIRouter(prefix="/admin/api/webhooks", tags=["admin-webhooks"], dependencies=[Depends(require_csrf)])


# ── Schemas ──────────────────────────────────────────────────────────

class WebhookOut(BaseModel):
    """Never carries `secret` — see webhook_service.py. A GET response
    for a webhook is indistinguishable in shape whether or not the
    caller ever saw the plaintext secret; that's by design."""
    id: str
    url: str
    events: list[str]
    is_active: bool


class WebhookCreateOut(WebhookOut):
    secret: str  # present only in the creation response, exactly once


class SecretOut(BaseModel):
    secret: str


class DeliveryOut(BaseModel):
    id: str
    event: str
    payload: dict[str, Any]
    response_status: int | None
    duration_ms: int
    attempted_at: str


class WebhookCreateIn(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    events: list[str] = Field(min_length=1)
    is_active: bool = True


class WebhookUpdateIn(BaseModel):
    url: str | None = Field(default=None, max_length=2048)
    events: list[str] | None = None
    is_active: bool | None = None


def _webhook_dict(w) -> dict[str, Any]:
    return dict(id=w.id, url=w.url, events=list(w.events), is_active=w.is_active)


def _delivery_dict(d) -> dict[str, Any]:
    return dict(
        id=d.id, event=d.event, payload=d.payload, response_status=d.response_status,
        duration_ms=d.duration_ms, attempted_at=d.attempted_at.isoformat(),
    )


# ── CRUD ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[WebhookOut])
def list_webhooks(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import webhook_service
    return [WebhookOut(**_webhook_dict(w)) for w in webhook_service.list_webhooks(db)]


@router.post("", response_model=WebhookCreateOut)
def create_webhook(body: WebhookCreateIn, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import webhook_service
    try:
        webhook, plaintext_secret = webhook_service.create_webhook(
            db, url=body.url, events=body.events, is_active=body.is_active,
            actor_id=admin.id, actor_username=admin.username,
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.refresh(webhook)
    return WebhookCreateOut(**_webhook_dict(webhook), secret=plaintext_secret)


@router.patch("/{webhook_id}", response_model=WebhookOut)
def update_webhook(
    webhook_id: str, body: WebhookUpdateIn,
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    from app import webhook_service
    try:
        webhook = webhook_service.update_webhook(
            db, webhook_id, url=body.url, events=body.events, is_active=body.is_active,
            actor_id=admin.id, actor_username=admin.username,
        )
        db.commit()
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.refresh(webhook)
    return WebhookOut(**_webhook_dict(webhook))


@router.delete("/{webhook_id}")
def delete_webhook(webhook_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import webhook_service
    ok = webhook_service.delete_webhook(db, webhook_id, actor_id=admin.id, actor_username=admin.username)
    db.commit()
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No webhook {webhook_id!r}")
    return {"ok": True}


@router.post("/{webhook_id}/regenerate-secret", response_model=SecretOut)
def regenerate_secret(webhook_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import webhook_service
    try:
        plaintext_secret = webhook_service.regenerate_secret(db, webhook_id, actor_id=admin.id, actor_username=admin.username)
        db.commit()
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return SecretOut(secret=plaintext_secret)


# ── Deliveries & testing ─────────────────────────────────────────────

@router.get("/{webhook_id}/deliveries", response_model=list[DeliveryOut])
def list_deliveries(
    webhook_id: str, limit: int = 50, offset: int = 0,
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    from app import webhook_service
    if webhook_service.get_webhook(db, webhook_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No webhook {webhook_id!r}")
    limit = max(1, min(limit, 200))
    return [DeliveryOut(**_delivery_dict(d)) for d in webhook_service.list_deliveries(db, webhook_id, limit=limit, offset=offset)]


@router.post("/{webhook_id}/test", response_model=DeliveryOut)
def send_test_event(webhook_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import webhook_service
    try:
        delivery = webhook_service.send_test_event(db, webhook_id)
        db.commit()
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return DeliveryOut(**_delivery_dict(delivery))
