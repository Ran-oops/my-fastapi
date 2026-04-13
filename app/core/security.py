from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


ALGORITHM = "HS256"


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": now,
        "type": "access",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str | int) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": now,
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, token_type: str | None = None) -> str | None:
    """验证JWT token，可选验证token类型。

    Args:
        token: JWT token字符串
        token_type: 可选的token类型验证("access"或"refresh")

    Returns:
        subject (user_id) 或 None (验证失败)
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if token_type and payload.get("type") != token_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None


def verify_refresh_token(token: str) -> str | None:
    """验证refresh token。"""
    return verify_token(token, token_type="refresh")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
