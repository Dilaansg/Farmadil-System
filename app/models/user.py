import uuid
from enum import Enum

from sqlmodel import SQLModel, Field, Column, String
from app.models.base import AuditableBase


class UserRole(str, Enum):
    SUPERADMIN = "SUPERADMIN"
    ADMIN = "ADMIN"
    CAJERO = "CAJERO"


class User(AuditableBase, table=True):
    __tablename__ = "users"
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, 
        primary_key=True, 
        index=True, 
        nullable=False
    )
    email: str = Field(
        sa_column=Column("email", String, unique=True, index=True, nullable=False)
    )
    password_hash: str = Field(nullable=False)
    rol: UserRole = Field(default=UserRole.CAJERO, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
