"""
app/tests/integration/test_regression_business_flows.py
─────────────────────────────────────────────────────────
Regression tests for critical business flows:
- Purchases (preview, confirm with auto-product creation)
- Products (full-field persistence)
- POS (add-item, checkout)
"""

import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlmodel import select

from app.models.product import Product
from app.models.purchase import PurchaseOrder, PurchaseOrderDetail, PurchaseStatus, Supplier


@pytest.mark.asyncio
class TestPurchaseAutoCreation:
    """Test that confirm_ingesta auto-creates products for unlinked items."""

    async def test_confirm_ingesta_auto_creates_product_for_new_item(self, client: AsyncClient, db_session):
        """
        Given: A DRAFT purchase order with a detail that has no producto_id
        When: We confirm the ingesta
        Then: A new product should be auto-created and linked to that detail
        """
        # Setup: Create supplier and draft order with unlinked item
        supplier = Supplier(nit="800123456", nombre_comercial="TestLab SAS")
        db_session.add(supplier)
        await db_session.commit()

        order = PurchaseOrder(
            supplier_id=supplier.id,
            numero_factura="INV-TEST-001",
            estado=PurchaseStatus.DRAFT,
            monto_total=Decimal("100000")
        )
        db_session.add(order)
        await db_session.flush()

        # Add detail with NO producto_id (simulates new unlinked item)
        detail = PurchaseOrderDetail(
            purchase_order_id=order.id,
            producto_id=None,  # ← No product linked
            nombre_factura="Test Medication XYZ",
            cantidad=10,
            costo_unitario=Decimal("5000")
        )
        db_session.add(detail)
        await db_session.commit()

        # Act: Confirm ingesta (should trigger auto-creation)
        response = await client.post(f"/api/v1/purchases/confirm/{order.id}")

        # Assert: HTTP 200 success response
        assert response.status_code == 200
        assert "Inventario Abastecido" in response.text

        # Verify: New product was created in DB
        result = await db_session.execute(select(Product).where(
            Product.nombre == "Test Medication XYZ"
        ))
        created_product = result.scalar_one_or_none()
        assert created_product is not None
        assert created_product.stock_actual == 10
        assert created_product.precio_compra == Decimal("5000")
        
        # Verify: Detail is now linked to new product
        result = await db_session.execute(select(PurchaseOrderDetail).where(
            PurchaseOrderDetail.id == detail.id
        ))
        updated_detail = result.scalar_one()
        assert updated_detail.producto_id == created_product.id

        # Verify: Order status is CONFIRMED
        result = await db_session.execute(select(PurchaseOrder).where(
            PurchaseOrder.id == order.id
        ))
        confirmed_order = result.scalar_one()
        assert confirmed_order.estado == PurchaseStatus.CONFIRMED


@pytest.mark.asyncio
class TestProductFullFieldPersistence:
    """Test that all product fields (including pharmaceutical data) are persisted."""

    async def test_create_product_persists_all_extended_fields(self, client: AsyncClient, db_session):
        """
        Given: A ProductCreate payload with all fields (including INVIMA, laboratorio, etc)
        When: POST /api/v1/products/
        Then: All fields are saved to the database
        """
        payload = {
            "codigo_barras": "7701234000012",
            "nombre": "Amoxicilina 500mg",
            "categoria": "Antibiótico",
            "precio_compra": 2500.0,
            "precio_venta": 5000.0,
            "stock_actual": 100,
            "stock_minimo": 10,
            "unidades_por_caja": 12,
            "registro_invima": "INVIMA-2024-001234",
            "principio_activo": "Amoxicilina trihidratada",
            "estado_invima": "Vigente",
            "laboratorio": "PharmaCorp SA"
        }

        response = await client.post(
            "/api/v1/products/",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 201
        product_data = response.json()

        # Verify all extended fields in response
        assert product_data["registro_invima"] == "INVIMA-2024-001234"
        assert product_data["principio_activo"] == "Amoxicilina trihidratada"
        assert product_data["estado_invima"] == "Vigente"
        assert product_data["laboratorio"] == "PharmaCorp SA"
        assert product_data["unidades_por_caja"] == 12

        # Verify persistence in DB
        result = await db_session.execute(select(Product).where(
            Product.codigo_barras == "7701234000012"
        ))
        persisted = result.scalar_one()
        assert persisted.registro_invima == "INVIMA-2024-001234"
        assert persisted.principio_activo == "Amoxicilina trihidratada"
        assert persisted.laboratorio == "PharmaCorp SA"

    async def test_update_product_persists_extended_fields(self, client: AsyncClient, db_session):
        """
        Given: An existing product
        When: PATCH with extended fields (registro_invima, laboratorio, etc)
        Then: All fields are updated in database
        """
        # Setup: Create initial product with minimal fields
        product = Product(
            codigo_barras="7701234000020",
            nombre="Ibuprofen 400mg",
            stock_actual=50,
            stock_minimo=5,
        )
        db_session.add(product)
        await db_session.commit()

        product_id = product.id

        # Act: Update with extended fields
        update_payload = {
            "registro_invima": "INVIMA-2024-005678",
            "principio_activo": "Ibuprofeno",
            "laboratorio": "PharmaPlus Inc",
            "estado_invima": "Vigente",
            "unidades_por_caja": 20
        }

        response = await client.patch(
            f"/api/v1/products/{product_id}",
            json=update_payload,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200

        # Verify DB persistence
        result = await db_session.execute(select(Product).where(
            Product.id == product_id
        ))
        updated = result.scalar_one()
        assert updated.registro_invima == "INVIMA-2024-005678"
        assert updated.laboratorio == "PharmaPlus Inc"
        assert updated.unidades_por_caja == 20


@pytest.mark.asyncio
class TestPOSCheckout:
    """Test Point-of-Sale checkout flow."""

    async def test_pos_add_item_increases_product_stock_info(self, client: AsyncClient, db_session):
        """
        Given: A product with available stock
        When: POST /api/v1/sales/add-item with codigo_barras
        Then: Response contains product details and total is updated
        """
        # Setup: Create a product with stock
        product = Product(
            codigo_barras="BARCODE-TEST-001",
            nombre="Test Product A",
            precio_venta=Decimal("5000"),
            stock_actual=30,
            stock_minimo=5
        )
        db_session.add(product)
        await db_session.commit()

        # Act: Add item to cart
        response = await client.post(
            "/api/v1/sales/add-item",
            data={
                "codigo_barras": "BARCODE-TEST-001",
                "current_total": "0"
            }
        )

        # Assert: Response contains product info
        assert response.status_code == 200
        assert "Test Product A" in response.text
        assert "BARCODE-TEST-001" in response.text or "Test%20Product%20A" in response.text
        assert "5000" in response.text  # Price present

    async def test_pos_add_item_fails_for_out_of_stock(self, client: AsyncClient, db_session):
        """
        Given: A product with 0 stock
        When: POST /api/v1/sales/add-item
        Then: Response contains "Sin stock" warning
        """
        # Setup: Out-of-stock product
        product = Product(
            codigo_barras="BARCODE-EMPTY",
            nombre="Out of Stock Item",
            precio_venta=Decimal("2000"),
            stock_actual=0,
            stock_minimo=5
        )
        db_session.add(product)
        await db_session.commit()

        # Act
        response = await client.post(
            "/api/v1/sales/add-item",
            data={
                "codigo_barras": "BARCODE-EMPTY",
                "current_total": "0"
            }
        )

        # Assert: Warning alert in response
        assert response.status_code == 200
        assert "Sin stock" in response.text

    async def test_pos_add_item_fails_for_nonexistent_barcode(self, client: AsyncClient, db_session):
        """
        Given: Non-existent barcode
        When: POST /api/v1/sales/add-item
        Then: Response contains "Producto no encontrado" error
        """
        response = await client.post(
            "/api/v1/sales/add-item",
            data={
                "codigo_barras": "BARCODE-NONEXISTENT",
                "current_total": "0"
            }
        )

        assert response.status_code == 200
        assert "no encontrado" in response.text or "Producto" in response.text


# End of test file
