import uuid
from datetime import datetime, timezone
from enum import Enum
from decimal import Decimal
from typing import Optional, List
from sqlmodel import Field, Relationship

from app.models.base import AuditableBase

class Supplier(AuditableBase, table=True):
    """
    Modelo de Proveedor para gestión de abastecimiento.
    """
    __tablename__ = "suppliers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    nit: str = Field(unique=True, index=True, description="NIT o Documento de Identidad del proveedor")
    nombre_comercial: str = Field(nullable=False)
    razon_social: Optional[str] = Field(default=None)
    telefono: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    
    # Historial de compras asociadas al proveedor
    compras: List["PurchaseOrder"] = Relationship(back_populates="proveedor")

class PurchaseStatus(str, Enum):
    DRAFT = "DRAFT"         # Pre-visualización, sin afectar inventario
    CONFIRMED = "CONFIRMED" # Carga aceptada y stock sumado
    CANCELLED = "CANCELLED" # Orden anulada

class PurchaseOrder(AuditableBase, table=True):
    """
    Representa una Factura de Compra o Ingreso de Mercancía.
    """
    __tablename__ = "purchase_orders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    supplier_id: Optional[uuid.UUID] = Field(default=None, foreign_key="suppliers.id")
    
    numero_factura: str = Field(index=True, description="Número de la factura física o electrónica")
    estado: PurchaseStatus = Field(default=PurchaseStatus.DRAFT)
    
    monto_total: Decimal = Field(default=0, max_digits=12, decimal_places=2)
    fecha_emision: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relación Inversa
    proveedor: Optional[Supplier] = Relationship(back_populates="compras")
    
    # Detalle de la compra (qué productos se compraron, cantidad y su costo unitario)
    detalles: List["PurchaseOrderDetail"] = Relationship(back_populates="orden_compra")


class PurchaseOrderDetail(AuditableBase, table=True):
    """
    Representa cada línea de producto dentro de una factura de compra.
    """
    __tablename__ = "purchase_order_details"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    
    purchase_order_id: uuid.UUID = Field(foreign_key="purchase_orders.id", nullable=False)
    
    # En la pre-visualización, puede que el producto no exista en la DB (nuevo medicamento)
    # Por lo que producto_id puede ser nulo hasta que se haga el match.
    producto_id: Optional[uuid.UUID] = Field(default=None, foreign_key="products.id")
    
    # Datos tal cual vienen de la factura (invaluable para auditoría o nuevos productos)
    nombre_factura: str = Field(nullable=False, description="Nombre exacto según proveedor")
    codigo_barras_factura: Optional[str] = Field(default=None)
    
    cantidad: int = Field(nullable=False)
    costo_unitario: Decimal = Field(nullable=False, max_digits=12, decimal_places=2)

    orden_compra: PurchaseOrder = Relationship(back_populates="detalles")
