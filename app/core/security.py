"""
app/core/security.py
────────────────────
Utilidades de seguridad: hashing de passwords y manejo de JWT tokens.

Funciones principales:
    hash_password(plain)        → str (bcrypt hash)
    verify_password(plain, hash) → bool
    create_access_token(data)   → str (JWT)
    create_refresh_token(data)  → str (JWT)
    decode_token(token)         → dict | None
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Password Hashing ─────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Genera un hash bcrypt del password en texto plano."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compara un password en texto plano con su hash. Seguro frente a timing attacks."""
    return _pwd_context.verify(plain_password, hashed_password)


# ── JWT Tokens ───────────────────────────────────────────────────────
def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    """Base interna para crear tokens JWT."""
    payload = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    payload.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(data: dict[str, Any]) -> str:
    """
    Crea un JWT de acceso de corta duración.

    Args:
        data: Payload del token. Convención: incluir {"sub": user_id_str, "type": "access"}
    """
    return _create_token(
        data={**data, "type": "access"},
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Crea un JWT de refresh de larga duración.

    Args:
        data: Payload del token. Convención: incluir {"sub": user_id_str, "type": "refresh"}
    """
    return _create_token(
        data={**data, "type": "refresh"},
        expires_delta=timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any] | None:
    """
    Decodifica y valida un JWT.

    Returns:
        El payload como diccionario, o None si el token es inválido/expirado.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None
