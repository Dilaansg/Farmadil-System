"""
app/schemas/token.py
─────────────────────
Schemas de tokens JWT para las respuestas de autenticación.
"""
from pydantic import BaseModel


class Token(BaseModel):
    """Response body del endpoint /auth/login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Payload decodificado de un JWT."""

    sub: str           # subject: user_id como string
    type: str          # "access" | "refresh"
    exp: int | None = None
    iat: int | None = None
