import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate

class ProductService:
    def __init__(self, session: AsyncSession):
        self.repo = ProductRepository(session)

    async def get_by_id(self, product_id: uuid.UUID) -> Product:
        product = await self.repo.get_by_id(product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
        return product

    async def get_by_codigo(self, codigo_barras: str) -> Product | None:
        return await self.repo.get_by_codigo_barras(codigo_barras)

    async def create_product(self, data: ProductCreate) -> Product:
        existing = await self.repo.get_by_codigo_barras(data.codigo_barras)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El código de barras ya está registrado")
        
        product = Product(
            codigo_barras=data.codigo_barras,
            nombre=data.nombre,
            categoria=data.categoria,
            precio_compra=data.precio_compra,
            precio_venta=data.precio_venta,
            stock_actual=data.stock_actual,
            stock_minimo=data.stock_minimo
        )
        return await self.repo.create(product)

    async def update_product(self, product_id: uuid.UUID, data: ProductUpdate) -> Product:
        product = await self.get_by_id(product_id)
        
        if data.codigo_barras and data.codigo_barras != product.codigo_barras:
            existing = await self.repo.get_by_codigo_barras(data.codigo_barras)
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El código de barras ya registrado por otro producto")
            product.codigo_barras = data.codigo_barras
            
        if data.nombre is not None: product.nombre = data.nombre
        if data.categoria is not None: product.categoria = data.categoria
        if data.precio_compra is not None: product.precio_compra = data.precio_compra
        if data.precio_venta is not None: product.precio_venta = data.precio_venta
        if data.stock_actual is not None: product.stock_actual = data.stock_actual
        if data.stock_minimo is not None: product.stock_minimo = data.stock_minimo
        
        return await self.repo.update(product)

    async def list_products(self, skip: int = 0, limit: int = 100) -> Sequence[Product]:
        return await self.repo.list_all(skip, limit)

    async def list_critical_stock(self) -> Sequence[Product]:
        return await self.repo.get_critical_stock()

    async def search_products(self, query: str, limit: int = 10) -> Sequence[Product]:
        return await self.repo.search(query, limit)

    async def delete_product(self, product_id: uuid.UUID) -> None:
        product = await self.get_by_id(product_id)
        await self.repo.soft_delete(product)
