from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app import content_service
from app.db import get_db

router = APIRouter(prefix="/api/content", tags=["public-content"])


@router.get("/pages")
def public_pages(response: Response, db: Session = Depends(get_db)):
    """All visible pages, every language at once (small payload, and it
    lets the frontend switch languages instantly with no refetch)."""
    response.headers["Cache-Control"] = "public, max-age=30"
    pages = content_service.list_pages(db, visible_only=True)
    return [
        {
            "slug": p.slug,
            "order": p.order,
            "show_in_nav": p.show_in_nav,
            "translations": p.translations,
        }
        for p in pages
    ]


@router.get("/faq")
def public_faq(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "public, max-age=30"
    items = content_service.list_faq(db, active_only=True)
    return [{"id": i.id, "translations": i.translations} for i in items]
