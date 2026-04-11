from datetime import datetime, timezone
from sqlmodel import SQLModel, Field

class AuditableBase(SQLModel):
    """
    Clase base abstracta para dotar de trazabilidad (Habeas Data) 
    y soft-delete a cualquier entidad del sistema.
    """
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    is_deleted: bool = Field(default=False, nullable=False)
