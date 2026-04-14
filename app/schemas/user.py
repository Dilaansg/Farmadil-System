import uuid
from datetime import datetime
import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints, field_validator

from app.models.user import UserRole

PasswordStr = Annotated[
    str,
    StringConstraints(
        min_length=8,
        max_length=72,
    ),
]


class UserCreate(BaseModel):
    email: EmailStr
    password: PasswordStr
    rol: UserRole = UserRole.CAJERO

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not re.search(r"[a-z]", value):
            raise ValueError("La contraseña debe incluir al menos una letra minúscula")
        if not re.search(r"[A-Z]", value):
            raise ValueError("La contraseña debe incluir al menos una letra mayúscula")
        if not re.search(r"\d", value):
            raise ValueError("La contraseña debe incluir al menos un número")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: PasswordStr


class UserPublic(BaseModel):
    id: uuid.UUID
    email: EmailStr
    rol: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: PasswordStr | None = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
