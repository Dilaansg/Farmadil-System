import uuid
from typing import Sequence
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product

class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, product_id: uuid.UUID) -> Product | None:
        statement = select(Product).where(Product.id == product_id, Product.is_deleted == False)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_codigo_barras(self, codigo_barras: str) -> Product | None:
        statement = select(Product).where(Product.codigo_barras == codigo_barras, Product.is_deleted == False)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_critical_stock(self) -> Sequence[Product]:
        """Retorna productos cuyo stock actual es menor o igual al stock mínimo."""
        statement = select(Product).where(
            Product.stock_actual <= Product.stock_minimo,
            Product.is_deleted == False
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_all(self, skip: int = 0, limit: int = 100) -> Sequence[Product]:
        statement = select(Product).where(Product.is_deleted == False).offset(skip).limit(limit)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def search(self, query: str, limit: int = 10) -> Sequence[Product]:
        """Busca productos por nombre o código de barras (case-insensitive)."""
        from sqlalchemy import or_
        statement = select(Product).where(
            or_(
                Product.nombre.ilike(f"%{query}%"),
                Product.codigo_barras.ilike(f"%{query}%")
            ),
            Product.is_deleted == False
        ).limit(limit)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def create(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def update(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def soft_delete(self, product: Product) -> None:
        product.is_deleted = True
        self.session.add(product)
        await self.session.commit()
