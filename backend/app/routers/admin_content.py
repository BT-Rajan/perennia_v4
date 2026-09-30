from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.content_schema import FAQ_FIELDS, PAGE_FIELDS
from app.db import get_db
from app.deps import get_current_admin, require_csrf
from app.models import AdminUser

router = APIRouter(prefix="/admin/api/content", tags=["admin-content"], dependencies=[Depends(require_csrf)])


# ── Schemas ──────────────────────────────────────────────────────────

class PageSchemaOut(BaseModel):
    fields: list[dict]


class PageOut(BaseModel):
    slug: str
    order: int
    is_visible: bool
    show_in_nav: bool
    translations: dict[str, dict[str, str]]


class PageUpsertIn(BaseModel):
    translations: dict[str, dict[str, str]]
    order: int | None = None
    is_visible: bool | None = None
    show_in_nav: bool | None = None


class PageReorderIn(BaseModel):
    ordered_slugs: list[str]


class VersionOut(BaseModel):
    id: str
    saved_at: str
    saved_by_username: str | None
    translations: dict[str, dict[str, str]]


class FaqOut(BaseModel):
    id: str
    order: int
    is_active: bool
    translations: dict[str, dict[str, str]]


class FaqUpsertIn(BaseModel):
    translations: dict[str, dict[str, str]]
    order: int = 0
    is_active: bool = True


class FaqReorderIn(BaseModel):
    ordered_ids: list[str]


# ── Pages ────────────────────────────────────────────────────────────

@router.get("/pages/schema", response_model=PageSchemaOut)
def page_schema(_: AdminUser = Depends(get_current_admin)):
    return PageSchemaOut(fields=[f.__dict__ for f in PAGE_FIELDS])


@router.get("/pages", response_model=list[PageOut])
def list_pages(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import content_service
    return [PageOut(**_page_dict(p)) for p in content_service.list_pages(db, visible_only=False)]


@router.get("/pages/{slug}", response_model=PageOut)
def get_page(slug: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import content_service
    page = content_service.get_page(db, slug)
    if page is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No page {slug!r}")
    return PageOut(**_page_dict(page))


@router.put("/pages/{slug}", response_model=PageOut)
def upsert_page(slug: str, body: PageUpsertIn, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import content_service
    try:
        page = content_service.upsert_page(
            db, slug, translations=body.translations, order=body.order,
            is_visible=body.is_visible, show_in_nav=body.show_in_nav,
            actor_id=admin.id, actor_username=admin.username,
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.refresh(page)
    return PageOut(**_page_dict(page))


@router.delete("/pages/{slug}")
def delete_page(slug: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import content_service
    ok = content_service.delete_page(db, slug, actor_id=admin.id, actor_username=admin.username)
    db.commit()
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No page {slug!r}")
    return {"ok": True}


@router.post("/pages/reorder")
def reorder_pages(body: PageReorderIn, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import content_service
    try:
        content_service.reorder_pages(db, body.ordered_slugs, actor_id=admin.id, actor_username=admin.username)
        db.commit()
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return {"ok": True}


@router.get("/pages/{slug}/versions", response_model=list[VersionOut])
def page_versions(slug: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import content_service
    return [
        VersionOut(id=v.id, saved_at=v.saved_at.isoformat(), saved_by_username=v.saved_by_username,
                   translations=v.translations)
        for v in content_service.list_versions(db, slug)
    ]


@router.post("/pages/{slug}/rollback/{version_id}", response_model=PageOut)
def rollback_page(slug: str, version_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import content_service
    try:
        page = content_service.rollback_page(db, slug, version_id, actor_id=admin.id, actor_username=admin.username)
        db.commit()
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.refresh(page)
    return PageOut(**_page_dict(page))


def _page_dict(p) -> dict[str, Any]:
    return dict(slug=p.slug, order=p.order, is_visible=p.is_visible, show_in_nav=p.show_in_nav,
                translations=p.translations)


# ── FAQ ─────────────────────────────────────────────────────────────

@router.get("/faq/schema", response_model=PageSchemaOut)
def faq_schema(_: AdminUser = Depends(get_current_admin)):
    return PageSchemaOut(fields=[f.__dict__ for f in FAQ_FIELDS])


@router.get("/faq", response_model=list[FaqOut])
def list_faq(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import content_service
    return [FaqOut(id=i.id, order=i.order, is_active=i.is_active, translations=i.translations)
            for i in content_service.list_faq(db, active_only=False)]


@router.post("/faq", response_model=FaqOut)
def create_faq(body: FaqUpsertIn, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import content_service
    try:
        item = content_service.create_faq(db, translations=body.translations, order=body.order,
                                           is_active=body.is_active, actor_id=admin.id, actor_username=admin.username)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.refresh(item)
    return FaqOut(id=item.id, order=item.order, is_active=item.is_active, translations=item.translations)


@router.put("/faq/{item_id}", response_model=FaqOut)
def update_faq(item_id: str, body: FaqUpsertIn, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import content_service
    try:
        item = content_service.update_faq(db, item_id, translations=body.translations, order=body.order,
                                           is_active=body.is_active, actor_id=admin.id, actor_username=admin.username)
        db.commit()
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.refresh(item)
    return FaqOut(id=item.id, order=item.order, is_active=item.is_active, translations=item.translations)


@router.delete("/faq/{item_id}")
def delete_faq(item_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import content_service
    ok = content_service.delete_faq(db, item_id, actor_id=admin.id, actor_username=admin.username)
    db.commit()
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No FAQ item {item_id!r}")
    return {"ok": True}


@router.post("/faq/reorder")
def reorder_faq(body: FaqReorderIn, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    from app import content_service
    try:
        content_service.reorder_faq(db, body.ordered_ids, actor_id=admin.id, actor_username=admin.username)
        db.commit()
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return {"ok": True}
