from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.settings_service import get_all

router = APIRouter(prefix="/api/config", tags=["public-config"])


@router.get("/public")
def public_config(response: Response, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Everything the frontend needs to render itself with zero hardcoded
    values: branding, theme, contact, locale, feature flags. Secret-typed
    settings are structurally excluded by get_all(include_secrets=False)
    — there is no field here that could ever leak a credential."""
    response.headers["Cache-Control"] = "public, max-age=30"
    return get_all(db, include_secrets=False)
