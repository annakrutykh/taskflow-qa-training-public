"""Бизнес-логика регистрации и аутентификации (CLAUDE.md, раздел 5)."""

import logging
import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.config import settings
from app.core.defects import defects
from app.core.errors import EmailAlreadyExistsError, InvalidCredentialsError
from app.core.redis_client import redis_client
from app.models import User

logger = logging.getLogger("app.auth")

pwd = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def register_user(
    db: Session,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
) -> User:
    """Создаёт нового пользователя с ролью USER.

    Бросает: EmailAlreadyExistsError, если email уже занят активным
    пользователем.
    """
    if db.query(User).filter(User.email == email, User.deleted_at.is_(None)).first():
        raise EmailAlreadyExistsError("Email exists")

    user = User(
        email=email,
        password_hash=pwd.hash(password),
        first_name=first_name,
        last_name=last_name,
    )

    db.add(user)
    db.flush()

    record_audit(db, user, "user.register", "user", user.id)

    db.commit()
    db.refresh(user)

    return user


def authenticate_user(db: Session, email: str, password: str) -> str:
    """Проверяет учётные данные и выдаёт JWT accessToken (8 часов).

    Бросает: InvalidCredentialsError, если email/пароль неверны или
    пользователь деактивирован.
    """
    if defects.is_enabled("D-17"):
        logger.warning(f"Login attempt: email={email} password={password}")

    user = db.query(User).filter(User.email == email, User.deleted_at.is_(None)).first()

    if not user or not user.is_active or not pwd.verify(password, user.password_hash):
        raise InvalidCredentialsError("Invalid credentials")

    token = jwt.encode(
        {
            "sub": str(user.id),
            "jti": uuid.uuid4().hex,
            "exp": datetime.now(UTC) + timedelta(hours=8),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    return token


def logout_user(jti: str | None, exp: int | None) -> None:
    """Отзывает текущий токен до конца его срока жизни.

    Токен хранится в блэклисте Redis ровно до момента истечения `exp` —
    после этого он и так стал бы невалиден, отдельно чистить не нужно.
    Токены, выпущенные до появления claim'а `jti` (jti is None), отозвать
    нельзя технически — logout в этом случае no-op.
    """
    if not jti or not exp:
        return

    remaining_seconds = max(exp - int(time.time()), 1)
    redis_client.setex(f"blacklist:{jti}", remaining_seconds, "1")
