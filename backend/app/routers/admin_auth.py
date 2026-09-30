import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_admin, get_current_session
from app.models import AdminSession, AdminUser, AuditLog
from app.rate_limit import limiter
from app.security import (
    SESSION_COOKIE_NAME,
    sign_session_id,
    verify_password,
)

router = APIRouter(prefix="/admin/api/auth", tags=["admin-auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    username: str
    role: str
    csrf_token: str


def _set_session_cookie(response: Response, signed_value: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=signed_value,
        max_age=settings.SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(request: Request, body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(AdminUser).where(AdminUser.username == body.username))

    # Constant-shape response whether the username exists or not, so this
    # endpoint doesn't leak which usernames are valid via timing or
    # response differences. verify_password() against a fixed dummy hash
    # keeps the bcrypt cost identical either way.
    dummy_hash = "$2b$12$C6UzMDM.H6dfI/f/IKcEeOfRRnf1x5Rk9M2qF8Qz2m1vgqQ8Y2N5S"
    ok = verify_password(body.password, user.password_hash if user else dummy_hash)

    if not user or not ok or not user.is_active:
        db.add(AuditLog(action="auth.login_failed", target=body.username,
                         ip_address=request.client.host if request.client else None))
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    sess = AdminSession(
        user_id=user.id,
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=settings.SESSION_TTL_SECONDS),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:255],
    )
    user.last_login_at = dt.datetime.now(dt.timezone.utc)
    db.add(sess)
    db.add(AuditLog(actor_id=user.id, actor_username=user.username, action="auth.login_success",
                     ip_address=request.client.host if request.client else None))
    db.commit()

    _set_session_cookie(response, sign_session_id(sess.id))
    return LoginResponse(username=user.username, role=user.role, csrf_token=sess.csrf_token)


@router.post("/logout")
def logout(response: Response, sess: AdminSession = Depends(get_current_session), db: Session = Depends(get_db)):
    db.delete(sess)
    db.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=LoginResponse)
def me(user: AdminUser = Depends(get_current_admin), sess: AdminSession = Depends(get_current_session)):
    return LoginResponse(username=user.username, role=user.role, csrf_token=sess.csrf_token)
