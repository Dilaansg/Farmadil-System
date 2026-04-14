from typing import Optional
from pydantic import BaseModel
from decimal import Decimal
from datetime import date

class ProductBase(BaseModel):
    codigo_barras: str
    nombre: str
    categoria: Optional[str] = None
    lote: str = "PENDIENTE"
    fecha_vencimiento: date = date(2099, 12, 31)
    marca_laboratorio: str = "SIN_MARCA"
    registro_invima: str = "SIN_REGISTRO"
    costo_caja: Decimal = Decimal('0.00')
    unidades_por_caja: int = 1
    precio_venta_unidad: Decimal = Decimal('0.00')

    # Compatibilidad con lógica histórica (se derivan si no llegan)
    precio_compra: Decimal = Decimal('0.00')
    precio_venta: Decimal = Decimal('0.00')
    image_url: Optional[str] = None
    stock_actual: int = 0
    stock_minimo: int
    principio_activo: Optional[str] = None
    estado_invima: Optional[str] = None
    laboratorio: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    codigo_barras: Optional[str] = None
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    lote: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    marca_laboratorio: Optional[str] = None
    registro_invima: Optional[str] = None
    costo_caja: Optional[Decimal] = None
    unidades_por_caja: Optional[int] = None
    precio_venta_unidad: Optional[Decimal] = None

    precio_compra: Optional[Decimal] = None
    precio_venta: Optional[Decimal] = None
    image_url: Optional[str] = None
    stock_actual: Optional[int] = None
    stock_minimo: Optional[int] = None
    principio_activo: Optional[str] = None
    estado_invima: Optional[str] = None
    laboratorio: Optional[str] = None
