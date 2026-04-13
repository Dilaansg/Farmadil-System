from typing import Optional
from pydantic import BaseModel
from decimal import Decimal

class ProductBase(BaseModel):
    codigo_barras: str
    nombre: str
    categoria: Optional[str] = None
    precio_compra: Decimal = Decimal('0.00')
    precio_venta: Decimal = Decimal('0.00')
    image_url: Optional[str] = None
    stock_actual: int = 0
    stock_minimo: int
    unidades_por_caja: int = 1
    registro_invima: Optional[str] = None
    principio_activo: Optional[str] = None
    estado_invima: Optional[str] = None
    laboratorio: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    codigo_barras: Optional[str] = None
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    precio_compra: Optional[Decimal] = None
    precio_venta: Optional[Decimal] = None
    image_url: Optional[str] = None
    stock_actual: Optional[int] = None
    stock_minimo: Optional[int] = None
    unidades_por_caja: Optional[int] = None
    registro_invima: Optional[str] = None
    principio_activo: Optional[str] = None
    estado_invima: Optional[str] = None
    laboratorio: Optional[str] = None
