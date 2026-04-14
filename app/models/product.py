import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from sqlmodel import Field

from app.models.base import AuditableBase

class Product(AuditableBase, table=True):
    """
    Modelo de Producto para la gestión de inventario.
    Hereda de AuditableBase (soft-delete, timestamps).
    """
    __tablename__ = "products"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, 
        primary_key=True, 
        index=True
    )
    codigo_barras: str = Field(
        unique=True, 
        index=True, 
        nullable=False,
        description="Código de barras único del producto."
    )
    nombre: str = Field(nullable=False)
    categoria: Optional[str] = Field(default=None)
    
    precio_compra: Decimal = Field(default=0, max_digits=10, decimal_places=2)
    precio_venta: Decimal = Field(default=0, max_digits=10, decimal_places=2)
    
    image_url: Optional[str] = Field(
        default=None, 
        description="URL de la imagen representativa del producto"
    )
    
    stock_actual: int = Field(default=0)
    stock_minimo: int = Field(
        nullable=False,
        description="Stock mínimo requerido. Diferente por la rotación de cada producto."
    )

    lote: str = Field(
        default="PENDIENTE",
        nullable=False,
        description="Lote de compra más reciente del producto"
    )
    fecha_vencimiento: date = Field(
        default=date(2099, 12, 31),
        nullable=False,
        description="Fecha de vencimiento del lote más reciente"
    )
    marca_laboratorio: str = Field(
        default="SIN_MARCA",
        nullable=False,
        description="Marca o laboratorio principal declarado en factura/catálogo"
    )
    costo_caja: Decimal = Field(
        default=0,
        nullable=False,
        max_digits=10,
        decimal_places=2,
        description="Costo de compra por caja"
    )
    unidades_por_caja: int = Field(
        default=1,
        nullable=False,
        description="Número de unidades (tabletas, sobres, etc.) que contiene una caja."
    )
    precio_venta_unidad: Decimal = Field(
        default=0,
        nullable=False,
        max_digits=10,
        decimal_places=2,
        description="Precio de venta por unidad individual"
    )

    # ── Datos de referencia farmacéutica (INVIMA) ─────────────────────────────
    registro_invima: str = Field(
        default="SIN_REGISTRO",
        nullable=False,
        index=True,
        description="Número de registro sanitario INVIMA (ej: INVIMA 2011M-0012292)"
    )
    principio_activo: Optional[str] = Field(
        default=None,
        description="Principio activo / genérico del medicamento"
    )
    estado_invima: Optional[str] = Field(
        default=None,
        description="Estado del registro INVIMA: Vigente, Vencido, Cancelado"
    )
    laboratorio: Optional[str] = Field(
        default=None,
        description="Laboratorio o titular fabricante del medicamento"
    )
