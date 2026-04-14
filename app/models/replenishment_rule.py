"""
app/models/replenishment_rule.py
─────────────────────────────────
Reglas de reposición automática para optimizar inventario.
Permite definir puntos de reorden, cantidad económica de compra, y proveedores preferidos.

Ejemplo:
- Si stock de Amoxicilina cae por debajo de 50 unidades,
  automáticamente crear una compra a LabX de 500 unidades.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field


class ReplenishmentRule(SQLModel, table=True):
    """Regla de reposición automática para un producto."""
    
    __tablename__ = "replenishment_rules"
    
    # Identidad
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    product_id: UUID = Field(foreign_key="product.id", index=True)
    supplier_id: Optional[UUID] = Field(default=None, foreign_key="supplier.id")
    
    # Parámetros de reorder
    punto_reorden: int = Field(ge=1)  # Stock mínimo que dispara compra
    cantidad_economica_compra: int = Field(ge=10)  # Cantidad óptima a ordenar
    
    # Control
    es_activa: bool = Field(default=True)
    dias_entrega_estimado: int = Field(default=5, ge=1)  # Para proyección
    
    # Prioridad (si hay múltiples proveedores)
    prioridad: int = Field(default=0)  # 0=primario, 1=secundario, etc
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440002",
                    "product_id": "550e8400-e29b-41d4-a716-446655440001",
                    "supplier_id": "550e8400-e29b-41d4-a716-446655440003",
                    "punto_reorden": 50,
                    "cantidad_economica_compra": 500,
                    "es_activa": True,
                    "dias_entrega_estimado": 5,
                    "prioridad": 0
                }
            ]
        }


class ReplenishmentLog(SQLModel, table=True):
    """Historial de reposiciones automáticas realizadas."""
    
    __tablename__ = "replenishment_logs"
    
    # Identidad
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    rule_id: UUID = Field(foreign_key="replenishment_rule.id")
    product_id: UUID = Field(foreign_key="product.id")
    supplier_id: Optional[UUID] = Field(foreign_key="supplier.id")
    
    # Datos de la compra automática
    cantidad_ordenada: int
    precio_unitario_compra: float
    monto_total: float
    
    # Estado
    estado: str = Field(default="pendiente")  # pendiente, confirmada, entregada
    numero_po: Optional[str] = None  # Referencia a la orden de compra
    
    # Timestamps
    fecha_orden: datetime = Field(default_factory=datetime.utcnow)
    fecha_entrega_estimada: Optional[datetime] = None
    fecha_entrega_real: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440004",
                    "rule_id": "550e8400-e29b-41d4-a716-446655440002",
                    "product_id": "550e8400-e29b-41d4-a716-446655440001",
                    "supplier_id": "550e8400-e29b-41d4-a716-446655440003",
                    "cantidad_ordenada": 500,
                    "precio_unitario_compra": 2500.0,
                    "monto_total": 1250000.0,
                    "estado": "confirmada",
                    "numero_po": "PO-2024-00001",
                    "fecha_orden": "2024-01-15T10:30:00",
                    "fecha_entrega_estimada": "2024-01-20T00:00:00"
                }
            ]
        }
