from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db
from app.db.models import User, UserSession

router = APIRouter(prefix="/api/auth", tags=["authentication"])
hasher = PasswordHasher()
attempts: dict[str, deque[float]] = defaultdict(deque)


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    confirm_password: str

    @model_validator(mode="after")
    def validate_password(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if not (
            any(c.islower() for c in self.password)
            and any(c.isupper() for c in self.password)
            and any(c.isdigit() for c in self.password)
        ):
            raise ValueError("Password must contain upper/lowercase letters and a number")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    id: int
    full_name: str
    email: str


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _session(db: Session, token: str | None) -> UserSession | None:
    if not token:
        return None
    session = db.scalar(select(UserSession).where(UserSession.token_hash == _hash_token(token)))
    if not session or session.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC):
        return None
    return session


def current_session(
    db: Annotated[Session, Depends(get_db)], geant_session: Annotated[str | None, Cookie()] = None
) -> UserSession:
    session = _session(db, geant_session)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def current_user(session: Annotated[UserSession, Depends(current_session)]) -> User:
    return session.user


def require_csrf(
    session: Annotated[UserSession, Depends(current_session)],
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> UserSession:
    if not x_csrf_token or not secrets.compare_digest(session.csrf_token, x_csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    return session


def _set_session(response: Response, db: Session, user: User) -> str:
    settings = get_settings()
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    db.add(
        UserSession(
            token_hash=_hash_token(token),
            csrf_token=csrf,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=settings.session_days),
        )
    )
    response.set_cookie(
        "geant_session",
        token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_days * 86400,
        path="/",
    )
    return csrf


@router.post("/register", status_code=201)
def register(body: RegisterRequest, response: Response, db: Annotated[Session, Depends(get_db)]):
    email = body.email.lower().strip()
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(
        full_name=body.full_name.strip(),
        email=email,
        password_hash=hasher.hash(body.password),
        created_at=datetime.now(UTC),
    )
    db.add(user)
    try:
        db.flush()
        csrf = _set_session(response, db, user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An account with this email already exists"
        ) from None
    return {
        "user": UserRead(id=user.id, full_name=user.full_name, email=user.email),
        "csrf_token": csrf,
    }


@router.post("/login")
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
):
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    bucket = attempts[key]
    while bucket and now - bucket[0] > 300:
        bucket.popleft()
    if len(bucket) >= 8:
        raise HTTPException(status_code=429, detail="Too many login attempts; try again later")
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower().strip()))
    try:
        valid = bool(user) and hasher.verify(user.password_hash, body.password)
    except VerifyMismatchError:
        valid = False
    if not valid:
        bucket.append(now)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    bucket.clear()
    csrf = _set_session(response, db, user)
    db.commit()
    return {
        "user": UserRead(id=user.id, full_name=user.full_name, email=user.email),
        "csrf_token": csrf,
    }


@router.get("/me")
def me(session: Annotated[UserSession, Depends(current_session)]):
    user = session.user
    return {
        "user": UserRead(id=user.id, full_name=user.full_name, email=user.email),
        "csrf_token": session.csrf_token,
    }


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    session: Annotated[UserSession, Depends(require_csrf)],
    db: Annotated[Session, Depends(get_db)],
):
    db.execute(delete(UserSession).where(UserSession.id == session.id))
    db.commit()
    response.delete_cookie("geant_session", path="/")
