import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, Request, status, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.dependencies.db import SessionDep
from app.services.sale_service import SaleService, SaleItem
from app.services.product_service import ProductService

router = APIRouter(prefix="/sales", tags=["POS y Ventas"])
templates = Jinja2Templates(directory="app/templates")

def get_sale_service(session: SessionDep) -> SaleService:
    return SaleService(session)

def get_product_service(session: SessionDep) -> ProductService:
    return ProductService(session)

@router.get("/pos", response_class=HTMLResponse)
async def pos_interface(request: Request):
    """
    Renderiza la interfaz del Punto de Venta (Terminal).
    """
    return templates.TemplateResponse(request=request, name="venta.html")

@router.post("/add-item", response_class=HTMLResponse)
async def add_pos_item(
    codigo_barras: str = Form(...),
    current_total: Decimal = Form(Decimal("0.0")),
    product_service: ProductService = Depends(get_product_service)
):
    """
    Búsqueda directa del código de barras. 
    Se usa en el escáner de la interfaz POS.
    Devuelve la nueva fila del carrito y actualiza el total con OOB.
    """
    producto = await product_service.get_by_codigo(codigo_barras.strip())
    
    if not producto:
        # Swap OOB para mostrar una alerta temporal si no se encuentra
        return HTMLResponse(content=f"""
        <div id="pos-alerts" hx-swap-oob="true">
            <div class="bg-red-100 text-red-700 p-3 rounded mb-4 animate-pulse">Producto no encontrado: {codigo_barras}</div>
        </div>
        """, status_code=200)

    if producto.stock_actual <= 0:
        return HTMLResponse(content=f"""
        <div id="pos-alerts" hx-swap-oob="true">
            <div class="bg-orange-100 text-orange-700 p-3 rounded mb-4 animate-pulse">Sin stock: {producto.nombre}</div>
        </div>
        """, status_code=200)

    nuevo_total = current_total + producto.precio_venta

    html = f"""
    <!-- La fila del nuevo ítem que se agregará al tbody (hx-swap="beforeend") -->
    <tr class="border-b hover:bg-gray-50 transition-colors bg-white">
        <!-- Campos ocultos para el checkout final -->
        <input type="hidden" name="product_ids" value="{producto.id}">
        <input type="hidden" name="precios" value="{producto.precio_venta}">
        <input type="hidden" name="cantidades" value="1">
        
        <td class="p-4 text-sm text-gray-900 font-medium">{producto.codigo_barras}</td>
        <td class="p-4 text-sm text-gray-700 font-bold">{producto.nombre}</td>
        <td class="p-4 text-sm text-gray-500">${producto.precio_venta}</td>
        <td class="p-4 text-sm font-bold text-indigo-600">1</td>
        <td class="p-4 text-sm text-gray-900 font-bold">${producto.precio_venta}</td>
    </tr>

    <!-- Actualización OOB del Total Dinámico -->
    <div id="total-container" hx-swap-oob="true" class="bg-indigo-600 rounded-xl p-6 text-white shadow-lg">
        <p class="text-indigo-200 text-sm font-bold uppercase mb-1">Total a Cobrar</p>
        <span class="text-4xl font-extrabold tracking-tight">${nuevo_total}</span>
        <input type="hidden" id="current-total-input" name="current_total" value="{nuevo_total}">
    </div>

    <!-- Limpieza de las alertas y reset del input -->
    <div id="pos-alerts" hx-swap-oob="true"></div>
    """
    
    return HTMLResponse(content=html)

@router.get("/visual-catalog", response_class=HTMLResponse)
async def visual_catalog(
    product_service: ProductService = Depends(get_product_service)
):
    """
    Devuelve los productos en formato grid de tarjetas 
    para el modal de búsqueda visual del POS.
    """
    productos = await product_service.list_products(limit=50) # Traer primeros 50 para evitar sobrecarga visual
    
    html = ""
    for prod in productos:
        # Solo mostrar los que tienen inventario
        if prod.stock_actual <= 0:
            continue
            
        initials = "".join([w[0] for w in prod.nombre.split()[:2]]).upper()
        image_html = f'<img src="{prod.image_url}" alt="{prod.nombre}" class="w-full h-32 object-cover">' if prod.image_url else f'<div class="w-full h-32 bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-3xl font-bold">{initials}</div>'

        html += f"""
        <div class="bg-white rounded-xl shadow-md border border-gray-100 overflow-hidden hover:shadow-lg transition-shadow cursor-pointer group"
             hx-post="/api/v1/sales/add-item" 
             hx-vals='{{"codigo_barras": "{prod.codigo_barras}"}}' 
             hx-include="#current-total-input" 
             hx-target="#cart-body" 
             hx-swap="beforeend"
             onclick="closeCatalogModal()">
            
            {image_html}
            
            <div class="p-4">
                <h3 class="text-sm font-bold text-gray-900 leading-tight group-hover:text-indigo-600 transition-colors">{prod.nombre}</h3>
                <p class="text-xs text-gray-500 mt-1 mb-2">Ref: {prod.codigo_barras}</p>
                <div class="flex justify-between items-center">
                    <span class="text-lg font-black text-green-600">${prod.precio_venta}</span>
                    <span class="text-xs font-medium px-2 py-1 bg-gray-100 text-gray-600 rounded-lg">Stock: {prod.stock_actual}</span>
                </div>
            </div>
        </div>
        """
        
    if not html:
        html = '<div class="col-span-full text-center text-gray-500 py-8">No hay productos en inventario.</div>'

    return HTMLResponse(content=html)

@router.post("/checkout")
async def process_checkout(
    product_ids: List[uuid.UUID] = Form(default=[]),
    cantidades: List[int] = Form(default=[]),
    precios: List[Decimal] = Form(default=[]),
    sale_service: SaleService = Depends(get_sale_service)
):
    """
    Endpoint para finalizar la venta y generar la transacción contable.
    """
    if not product_ids:
        # En caso de mandar un panel vacío
        html = """
        <div id="pos-alerts" hx-swap-oob="true">
            <div class="bg-red-100 text-red-700 p-3 rounded mb-4">El carrito está vacío. Agrega productos primero.</div>
        </div>
        """
        return HTMLResponse(content=html)

    # Validar consistencia de los arrays
    if len(product_ids) != len(cantidades) or len(product_ids) != len(precios):
        raise HTTPException(status_code=400, detail="Formato de carrito inválido.")

    # Agrupar los ítems. Si se escaneó 3 veces el mismo, viene en 3 filas.
    # El diccionario agrupa por ID sumando cantidades para hacer un solo update por producto.
    items_map = {}
    for pid, cant, precio in zip(product_ids, cantidades, precios):
        if pid in items_map:
            items_map[pid].cantidad += cant
        else:
            items_map[pid] = SaleItem(product_id=pid, cantidad=cant, precio_unitario=precio)
    
    sale_items = list(items_map.values())

    try:
        transaccion = await sale_service.process_sale(items=sale_items, descripcion="Venta POS Mostrador")
    except ValueError as e:
        # Error de negocio (ej. falta de stock de algún ítem) que provocó Rollback
        html = f"""
        <div id="pos-alerts" hx-swap-oob="true">
            <div class="bg-red-100 text-red-700 p-4 rounded shadow font-bold text-lg">Error en venta: {str(e)}</div>
        </div>
        """
        return HTMLResponse(content=html)

    # 100% éxito: limpiar el carrito y mostrar éxito
    html_exito = f"""
    <!-- Limpiar el body del carrito -->
    <tbody id="cart-body" class="divide-y divide-gray-100"></tbody>

    <!-- Resetear el totalizador -->
    <div id="total-container" hx-swap-oob="true" class="bg-indigo-600 rounded-xl p-6 text-white shadow-lg">
        <p class="text-indigo-200 text-sm font-bold uppercase mb-1">Total a Cobrar</p>
        <span class="text-4xl font-extrabold tracking-tight">$0.00</span>
        <input type="hidden" id="current-total-input" name="current_total" value="0">
    </div>

    <!-- Mostrar la gran alerta de éxito -->
    <div id="pos-alerts" hx-swap-oob="true">
        <div class="bg-green-100 text-green-800 p-4 rounded shadow-sm border border-green-200 font-bold mb-4">
            ✅ Venta finalizada exitosamente. Total cobrado: ${transaccion.monto_total}
        </div>
    </div>
    """
    
    return HTMLResponse(content=html_exito)

