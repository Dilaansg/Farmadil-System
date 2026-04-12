import uuid
from decimal import Decimal
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.transaction import Transaction, TransactionDetail, TransactionType
from app.models.product import Product

class SaleItem:
    """Clase auxiliar para representar el DTO de entrada en una venta."""
    def __init__(self, product_id: uuid.UUID, cantidad: int, precio_unitario: Decimal):
        self.product_id = product_id
        self.cantidad = cantidad
        self.precio_unitario = precio_unitario

class SaleService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def process_sale(self, items: List[SaleItem], descripcion: str = "Venta POS") -> Transaction:
        """
        Procesa una venta de manera atómica (Transaccional).
        Si un producto no tiene stock, hace Rollback automático.
        """
        
        # Iniciar transacción a nivel de Base de Datos
        # Cualquier error dentro de este bloque revertirá automáticamente todos los INSERT/UPDATE
        async with self.session.begin():
            # 1. Crear el encabezado de la Transacción
            monto_total = sum((item.cantidad * item.precio_unitario) for item in items)
            
            nueva_transaccion = Transaction(
                tipo=TransactionType.INGRESO,
                monto_total=monto_total,
                descripcion=descripcion
            )
            self.session.add(nueva_transaccion)
            await self.session.flush() # Para obtener el ID de la transacción sin commitear aún

            # 2. Recorrer los items, verificar stock y descontar
            for item in items:
                # Obtener producto bloqueando la fila (opcional: with_for_update() en concurrencia alta)
                stmt = select(Product).where(Product.id == item.product_id)
                result = await self.session.execute(stmt)
                producto = result.scalar_one_or_none()

                if not producto:
                    raise ValueError(f"Producto con ID {item.product_id} no encontrado.")

                if producto.stock_actual < item.cantidad:
                    # El ValueError será capturado por el AsyncSession y hará ROLLBACK automático
                    raise ValueError(
                        f"Stock insuficiente para {producto.nombre}. "
                        f"Intentando vender {item.cantidad}, pero solo hay {producto.stock_actual}."
                    )

                # Descontar stock
                producto.stock_actual -= item.cantidad
                self.session.add(producto)

                # Crear detalle
                detalle = TransactionDetail(
                    transaccion_id=nueva_transaccion.id,
                    producto_id=producto.id,
                    cantidad=item.cantidad,
                    precio_unitario_historico=item.precio_unitario
                )
                self.session.add(detalle)

            # 3. Al terminar el bloque 'async with', si no hay errores se llama a COMMIT automáticamente.
            
        # Si llegamos aquí, se hizo commit
        return nueva_transaccion

