# api/dependencies/auth.py
"""JWT authentication and RBAC dependencies."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, Field

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "480"))


class Role(str, Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class TokenData(BaseModel):
    username: str
    role: Role
    exp: Optional[datetime] = None


class UserPublic(BaseModel):
    username: str
    role: Role
    disabled: bool = False


class UserInDB(UserPublic):
    hashed_password: str


class NoteCreate(BaseModel):
    note: str = Field(..., min_length=1, max_length=4000)


def _jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        secret = os.environ.get("JWT_SECRET_DEV", "dev-only-change-me")
    return secret


def _password_bytes(password: str) -> bytes:
    # bcrypt limit is 72 bytes
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_password_bytes(plain), hashed.encode("utf-8"))


_USERS: Optional[dict[str, UserInDB]] = None


def _bootstrap_users() -> dict[str, UserInDB]:
    users: dict[str, UserInDB] = {}
    admin_user = os.environ.get("ADMIN_USERNAME", "admin")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "admin-change-me")
    operator_user = os.environ.get("OPERATOR_USERNAME", "operator")
    operator_pass = os.environ.get("OPERATOR_PASSWORD", "operator-change-me")
    viewer_user = os.environ.get("VIEWER_USERNAME", "viewer")
    viewer_pass = os.environ.get("VIEWER_PASSWORD", "viewer-change-me")

    users[admin_user] = UserInDB(
        username=admin_user, role=Role.ADMIN, hashed_password=hash_password(admin_pass)
    )
    users[operator_user] = UserInDB(
        username=operator_user,
        role=Role.OPERATOR,
        hashed_password=hash_password(operator_pass),
    )
    users[viewer_user] = UserInDB(
        username=viewer_user, role=Role.VIEWER, hashed_password=hash_password(viewer_pass)
    )
    return users


def _users() -> dict[str, UserInDB]:
    global _USERS
    if _USERS is None:
        _USERS = _bootstrap_users()
    return _USERS


def get_user(username: str) -> Optional[UserInDB]:
    return _users().get(username)


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = get_user(username)
    if not user or user.disabled:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(
    username: str, role: Role, expires_delta: Optional[timedelta] = None
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": username, "role": role.value, "exp": expire}
    return jwt.encode(payload, _jwt_secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[ALGORITHM])
        username = payload.get("sub")
        role_raw = payload.get("role")
        if not username or not role_raw:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(username=username, role=Role(role_raw))
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> UserPublic:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    data = decode_token(token)
    user = get_user(data.username)
    if not user or user.disabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    return UserPublic(username=user.username, role=user.role, disabled=user.disabled)


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[UserPublic]:
    if not token:
        return None
    try:
        return await get_current_user(token)
    except HTTPException:
        return None


def require_roles(*roles: Role):
    allowed = set(roles)

    async def _checker(user: UserPublic = Depends(get_current_user)) -> UserPublic:
        if user.role in allowed or user.role == Role.ADMIN:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of: {[r.value for r in roles]}",
        )

    return _checker


async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user.username, user.role)
    return Token(access_token=token, role=user.role.value, username=user.username)
