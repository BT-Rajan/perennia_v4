from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.config import settings
from app.deps import get_current_admin, require_csrf
from app.models import AdminUser

router = APIRouter(prefix="/admin/api/uploads", tags=["admin-uploads"], dependencies=[Depends(require_csrf)])

# Sniffed from the file's actual bytes, never trusted from the
# client-supplied Content-Type header or filename extension — both are
# attacker-controlled. SVG is deliberately not accepted here: an SVG
# can embed <script> and event-handler attributes, so serving one
# back verbatim from this endpoint would be a stored-XSS vector. An
# admin who wants an SVG logo can still point branding.logo_url at one
# hosted elsewhere (the setting is a plain URL) — this endpoint just
# doesn't allow *uploading* one for us to re-serve.
_MAGIC_BYTES: dict[bytes, tuple[str, str]] = {
    b"\x89PNG\r\n\x1a\n": ("image/png", ".png"),
    b"\xff\xd8\xff": ("image/jpeg", ".jpg"),
    b"RIFF": ("image/webp", ".webp"),  # further checked below (RIFF is also used by other formats)
    b"\x00\x00\x01\x00": ("image/x-icon", ".ico"),
}


def _sniff_image_type(head: bytes) -> tuple[str, str] | None:
    for magic, result in _MAGIC_BYTES.items():
        if head.startswith(magic):
            if magic == b"RIFF":
                if len(head) >= 12 and head[8:12] == b"WEBP":
                    return result
                continue
            return result
    return None


@router.post("/image")
async def upload_image(file: UploadFile, admin: AdminUser = Depends(get_current_admin)):
    body = await file.read(settings.MAX_UPLOAD_IMAGE_BYTES + 1)
    if len(body) > settings.MAX_UPLOAD_IMAGE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                             f"Image exceeds {settings.MAX_UPLOAD_IMAGE_BYTES // (1024*1024)}MB limit")
    if not body:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")

    sniffed = _sniff_image_type(body[:16])
    if sniffed is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                             "Unsupported image type — PNG, JPEG, WEBP, and ICO are accepted.")
    _content_type, ext = sniffed

    # Random filename — never derived from the client-supplied name, so
    # there's no path-traversal surface and no collision/overwrite risk
    # between admins uploading around the same time.
    filename = f"{secrets.token_hex(16)}{ext}"
    dest = settings.UPLOADS_DIR / filename
    dest.write_bytes(body)

    return {"url": f"/uploads/{filename}"}
