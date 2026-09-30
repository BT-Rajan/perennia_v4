from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import knowledge_service
from app.db import get_db
from app.deps import get_current_admin, require_csrf
from app.models import AdminUser
from app.rate_limit import limiter
from app.config import settings as infra_settings

router = APIRouter(prefix="/admin/api/knowledge", tags=["admin-knowledge"], dependencies=[Depends(require_csrf)])

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB — matches the reference implementation's cap


class SourceOut(BaseModel):
    id: str
    kind: str
    content_type: str
    title: str
    source_ref: str
    chars: int
    truncated: bool
    is_active: bool
    ok: bool
    error_message: str
    created_at: str
    updated_at: str


class SourcePreviewOut(SourceOut):
    text: str


class AddUrlRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class SetActiveRequest(BaseModel):
    is_active: bool


def _serialize(s) -> SourceOut:
    return SourceOut(
        id=s.id, kind=s.kind, content_type=s.content_type, title=s.title, source_ref=s.source_ref,
        chars=s.chars, truncated=s.truncated, is_active=s.is_active, ok=s.ok, error_message=s.error_message,
        created_at=s.created_at.isoformat(), updated_at=s.updated_at.isoformat(),
    )


@router.get("", response_model=list[SourceOut])
def list_sources(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    return [_serialize(s) for s in knowledge_service.list_sources(db)]


@router.get("/{source_id}", response_model=SourcePreviewOut)
def get_source(source_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    s = knowledge_service.get_source(db, source_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No knowledge source {source_id!r}")
    return SourcePreviewOut(**_serialize(s).model_dump(), text=s.text)


@router.post("/upload", response_model=SourceOut)
@limiter.limit(infra_settings.RATE_LIMIT_KNOWLEDGE_UPLOAD)  # cap uploads to blunt disk-exhaustion DoS via repeated large files
async def upload_source(
    request: Request, file: UploadFile, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                             f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit")
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")

    from pathlib import Path
    filename = Path(file.filename or "upload").name  # strip any path components

    try:
        source = knowledge_service.create_from_upload(
            db, raw=raw, filename=filename, actor_id=admin.id, actor_username=admin.username,
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.commit()
    db.refresh(source)
    return _serialize(source)


@router.post("/url", response_model=SourceOut)
@limiter.limit(infra_settings.RATE_LIMIT_KNOWLEDGE_UPLOAD)
def add_url_source(
    request: Request, body: AddUrlRequest, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    try:
        source = knowledge_service.create_from_url(db, url=body.url, actor_id=admin.id, actor_username=admin.username)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.commit()
    db.refresh(source)
    return _serialize(source)


@router.post("/{source_id}/refresh", response_model=SourceOut)
@limiter.limit(infra_settings.RATE_LIMIT_KNOWLEDGE_UPLOAD)
def refresh_source(
    request: Request, source_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    try:
        source = knowledge_service.refresh_url_source(db, source_id, actor_id=admin.id, actor_username=admin.username)
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.commit()
    db.refresh(source)
    return _serialize(source)


@router.patch("/{source_id}", response_model=SourceOut)
def set_active(
    source_id: str, body: SetActiveRequest, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    try:
        source = knowledge_service.set_active(db, source_id, body.is_active, actor_id=admin.id, actor_username=admin.username)
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    db.commit()
    db.refresh(source)
    return _serialize(source)


@router.delete("/{source_id}")
def delete_source(source_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    ok = knowledge_service.delete_source(db, source_id, actor_id=admin.id, actor_username=admin.username)
    db.commit()
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No knowledge source {source_id!r}")
    return {"ok": True}
