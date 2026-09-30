from __future__ import annotations

import datetime as dt

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import AdminSession, AdminUser
from app.security import SESSION_COOKIE_NAME, unsign_session_id, csrf_tokens_match


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def get_current_session(
    db: Session = Depends(get_db),
    cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> AdminSession:
    if not cookie:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    session_id = unsign_session_id(cookie, max_age=settings.SESSION_TTL_SECONDS)
    if not session_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    sess = db.get(AdminSession, session_id)
    if sess is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session not found")
    if sess.expires_at.replace(tzinfo=dt.timezone.utc) < _utcnow():
        db.delete(sess)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    return sess


def get_current_admin(
    sess: AdminSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> AdminUser:
    user = db.get(AdminUser, sess.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account disabled")
    return user


def require_csrf(
    request: Request,
    sess: AdminSession = Depends(get_current_session),
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    """Every state-changing admin request (POST/PUT/PATCH/DELETE) must
    carry the session's CSRF token in a header — belt-and-suspenders
    alongside SameSite=Lax cookies, since this app may end up embedded
    or proxied in ways that weaken SameSite's protection."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    if not csrf_tokens_match(sess.csrf_token, x_csrf_token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF token missing or invalid")
