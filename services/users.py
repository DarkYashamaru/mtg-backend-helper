from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.users import User
from tools.password_hasher import InvalidPasswordHash, hash_password, verify_password


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,32}$")
MIN_PASSWORD_LENGTH = 8


class UserAlreadyExists(ValueError):
    """Raised when attempting to register a duplicate username."""


class InvalidUserData(ValueError):
    """Raised when user registration data is invalid."""


def normalize_username(username: str) -> str:
    if not isinstance(username, str):
        raise InvalidUserData("Username must be a string.")
    return username.strip()


def validate_username(username: str) -> str:
    normalized = normalize_username(username)
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise InvalidUserData(
            "Username must be 3-32 characters and only contain letters, numbers, or underscores."
        )
    return normalized


def validate_password(password: str) -> None:
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise InvalidUserData(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    normalized = normalize_username(username)
    statement = select(User).where(func.lower(User.username) == normalized.casefold())
    return db.execute(statement).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def create_user(
    db: Session,
    username: str,
    password: str,
    *,
    is_admin: bool = False,
    commit: bool = True,
) -> User:
    normalized_username = validate_username(username)
    validate_password(password)

    if get_user_by_username(db, normalized_username) is not None:
        raise UserAlreadyExists("Username is already registered.")

    user = User(
        username=normalized_username,
        password_hash=hash_password(password),
        is_admin=is_admin,
    )
    db.add(user)

    try:
        if commit:
            db.commit()
            db.refresh(user)
        else:
            db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise UserAlreadyExists("Username is already registered.") from exc

    return user


def authenticate_user(
    db: Session,
    username: str,
    password: str,
    *,
    ip_address: Optional[str] = None,
    commit: bool = True,
) -> Optional[User]:
    user = get_user_by_username(db, username)
    if user is None or not user.is_active:
        return None

    try:
        password_matches = verify_password(password, user.password_hash)
    except InvalidPasswordHash:
        password_matches = False

    if not password_matches:
        return None

    user.last_login = datetime.utcnow()
    user.login_count += 1
    user.last_ip = ip_address

    if commit:
        db.commit()
        db.refresh(user)
    else:
        db.flush()

    return user


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login": user.last_login,
        "login_count": user.login_count,
        "last_ip": user.last_ip,
    }
