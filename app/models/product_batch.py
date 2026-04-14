"""
app/models/product_batch.py
────────────────────────────
Modelo para gestionar lotes de productos con control de vencimientos.
Útil para farmacéutica donde cada lote tiene un número y fecha de vencimiento.

Ejemplo de uso:
- ProductBatch(product_id=..., numero_lote="3A2024", fecha_vencimiento=2025-12-31, cantidad=500)
"""

from datetime import datetime, date
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship


class ProductBatch(SQLModel, table=True):
    """Lote de un producto con código y fecha de vencimiento."""
    
    __tablename__ = "product_batches"
    
    # Identidad
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    product_id: UUID = Field(foreign_key="product.id")
    
    # Datos del lote
    numero_lote: str = Field(index=True)  # "3A2024", "BATCH-001", etc
    fecha_vencimiento: date  # Ej: 2025-12-31
    cantidad_disponible: int = Field(ge=0)  # Stock actual del lote
    cantidad_total: int  # Cantidad que llegó
    
    # Control
    estado_lote: str = Field(default="activo")  # activo, vencido, parcial
    fecha_recepcion: datetime = Field(default_factory=datetime.utcnow)
    precio_unitario_compra: Optional[float] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relación (lazy loading)
    product: Optional["Product"] = Relationship(back_populates="batches")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "product_id": "550e8400-e29b-41d4-a716-446655440001",
                    "numero_lote": "3A2024",
                    "fecha_vencimiento": "2025-12-31",
                    "cantidad_disponible": 480,
                    "cantidad_total": 500,
                    "estado_lote": "activo",
                    "fecha_recepcion": "2024-01-15T10:30:00",
                    "precio_unitario_compra": 2500.0
                }
            ]
        }


# ─── Actualizar Product para incluir relación con batches ───
# (Se debe importar este módulo en app/models/__init__.py)
# En app/models/product.py, agregar:
#
#   from typing import List, Optional
#   from sqlmodel import Relationship
#   
#   class Product(SQLModel, table=True):
#       ...
#       batches: List["ProductBatch"] = Relationship(back_populates="product")
#
# O usar un alias sin FK directo si prefieres evitar circular imports:
#   batches: Optional[List["ProductBatch"]] = Field(default=None, relationship=True)
