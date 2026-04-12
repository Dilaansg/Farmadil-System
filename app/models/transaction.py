import uuid
from enum import Enum
from decimal import Decimal
from typing import Optional, List
from datetime import datetime, timezone

from sqlmodel import Field, Relationship
from app.models.base import AuditableBase

class TransactionType(str, Enum):
    INGRESO = "INGRESO"
    EGRESO = "EGRESO"

class Transaction(AuditableBase, table=True):
    """
    Representa el encabezado de una transacción (Venta o Compra).
    """
    __tablename__ = "transactions"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, 
        primary_key=True, 
        index=True
    )
    tipo: TransactionType = Field(nullable=False)
    monto_total: Decimal = Field(default=0, max_digits=12, decimal_places=2)
    descripcion: Optional[str] = Field(default=None)
    fecha_hora: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # Campo recomendado: ¿quién hizo la venta?
    # user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")

    # Relación con los detalles
    detalles: List["TransactionDetail"] = Relationship(back_populates="transaccion")

class TransactionDetail(AuditableBase, table=True):
    """
    Representa cada línea de la transacción (los productos vendidos).
    """
    __tablename__ = "transaction_details"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, 
        primary_key=True, 
        index=True
    )
    
    transaccion_id: uuid.UUID = Field(foreign_key="transactions.id", nullable=False)
    producto_id: uuid.UUID = Field(foreign_key="products.id", nullable=False)
    
    cantidad: int = Field(nullable=False)
    precio_unitario_historico: Decimal = Field(nullable=False, max_digits=12, decimal_places=2)

    # Relación bidireccional
    transaccion: Transaction = Relationship(back_populates="detalles")

