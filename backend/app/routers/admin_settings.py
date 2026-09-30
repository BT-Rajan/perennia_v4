from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_admin, require_csrf
from app.models import AdminUser
from app.settings_registry import CATEGORIES, SettingType, defs_for_category
from app.settings_service import get_all, get_category, set_many, all_secret_placeholders

router = APIRouter(prefix="/admin/api/settings", tags=["admin-settings"], dependencies=[Depends(require_csrf)])


class SettingSchema(BaseModel):
    key: str
    category: str
    label: str
    type: SettingType
    default: Any
    help_text: str
    secret: bool
    choices: list[str] | None
    i18n: bool


class CategoryResponse(BaseModel):
    category: str
    schema_: list[SettingSchema]
    values: dict[str, Any]


@router.get("/categories")
def list_categories(_: AdminUser = Depends(get_current_admin)) -> list[str]:
    return CATEGORIES


@router.get("/{category}", response_model=CategoryResponse)
def get_settings_for_category(category: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    defs = defs_for_category(category)
    if not defs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown category: {category}")
    values = get_category(db, category)  # secrets already masked — see settings_service.get_category
    return CategoryResponse(
        category=category,
        schema_=[
            SettingSchema(
                key=d.key, category=d.category, label=d.label, type=d.type, default=d.default,
                help_text=d.help_text, secret=d.secret,
                choices=list(d.choices) if d.choices else None, i18n=d.i18n,
            ) for d in defs
        ],
        values=values,
    )


@router.put("/{category}")
def update_settings_for_category(
    category: str,
    body: dict[str, Any],
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    defs = defs_for_category(category)
    if not defs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown category: {category}")
    allowed_keys = {d.key for d in defs}
    unknown = set(body) - allowed_keys
    if unknown:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Keys not in category '{category}': {sorted(unknown)}")

    try:
        updated = set_many(
            db, body,
            actor_id=admin.id, actor_username=admin.username,
            ip_address=request.client.host if request.client else None,
        )
    except (KeyError, ValueError) as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    db.commit()
    if category == "calendar_sync" and "calendar_sync.drift_poll_minutes" in updated:
        from app import scheduler
        scheduler.reschedule(body["calendar_sync.drift_poll_minutes"])
    if category == "booking" and "booking.pending_expiry_poll_minutes" in updated:
        from app import scheduler
        scheduler.reschedule_pending_expiry(body["booking.pending_expiry_poll_minutes"])
    return {"updated": updated}


@router.get("")
def get_all_settings(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)) -> dict[str, Any]:
    """Everything, including secret values (masked), for a full-settings
    admin export/overview screen. Secrets are masked, never decrypted
    back to the browser — write-only from the admin's perspective."""
    out = get_all(db, include_secrets=False)
    out.update(all_secret_placeholders(db))
    return out
