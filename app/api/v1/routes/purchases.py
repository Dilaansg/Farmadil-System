import uuid
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select

from app.dependencies.db import SessionDep
from app.services.parser_service import ParserService
from app.models.product import Product
from app.models.purchase import Supplier, PurchaseOrder, PurchaseOrderDetail, PurchaseStatus

router = APIRouter(prefix="/purchases", tags=["Compras e Ingesta"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/ingesta", response_class=HTMLResponse)
async def ingesta_page(request: Request):
    """Renderiza la vista principal para arrastrar y soltar facturas."""
    return templates.TemplateResponse(request=request, name="ingesta_factura.html")

@router.post("/preview", response_class=HTMLResponse)
async def preview_invoice(
    session: SessionDep,
    file: UploadFile = File(...),
    margen_configurado: float = Form(0.35)
):
    """
    Recibe la factura (.xml o .xlsx), la parsea, la guarda como DRAFT 
    y devuelve la tabla de pre-visualización HTMX.
    """
    contents = await file.read()
    filename = file.filename.lower()
    
    try:
        if filename.endswith(".xlsx"):
            parsed_invoice = ParserService.parse_xlsx(contents)
        elif filename.endswith(".xml"):
            parsed_invoice = ParserService.parse_ubl_xml(contents)
        else:
            return HTMLResponse('<div class="text-red-500 font-bold p-4 bg-red-100 rounded">Formato no soportado. Usa .xml o .xlsx</div>')
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-500 font-bold p-4 bg-red-100 rounded">Error parseando factura: {str(e)}</div>')

    # 1. Obtener listado actual de productos en BD para el cálculo inteligente
    result = await session.execute(select(Product))
    products_db = {p.nombre.lower(): p for p in result.scalars().all()}
    
    # Evaluar precios para mostrar sugerencias
    parsed_invoice = ParserService.calculate_price_suggestions(
        parsed_invoice=parsed_invoice, 
        db_products=products_db, 
        margen_porcentual=margen_configurado
    )

    # 2. Persistencia Segura (DRAFT)
    # Buscar o crear proveedor
    sup_result = await session.execute(select(Supplier).where(Supplier.nit == parsed_invoice.proveedor_nit))
    supplier = sup_result.scalar_one_or_none()
    
    if not supplier:
        supplier = Supplier(nit=parsed_invoice.proveedor_nit, nombre_comercial=parsed_invoice.proveedor_nombre)
        session.add(supplier)
        await session.flush()
        
    # Crear la Orden DRAFT
    monto_total = sum(d.cantidad * d.costo_unitario for d in parsed_invoice.detalles)
    order = PurchaseOrder(
        supplier_id=supplier.id,
        numero_factura=parsed_invoice.numero_factura,
        estado=PurchaseStatus.DRAFT,
        monto_total=monto_total
    )
    session.add(order)
    await session.flush()
    
    # === Construir tabla HTML con inputs editables ===
    filas_html = ""
    for idx, d in enumerate(parsed_invoice.detalles):
        db_product_id = None
        
        # Clase visual si subió el costo
        tr_class = "bg-amber-50 border-l-4 border-amber-400" if d.subio_costo else "bg-white"
        alerta_subida = '<span class="text-xs bg-amber-200 text-amber-800 px-2 py-0.5 rounded-full">⚠️ Subió</span>' if d.subio_costo else ""
        
        # Enlazar producto existente
        matched_product = products_db.get(d.nombre_producto.lower())
        if matched_product:
            db_product_id = matched_product.id
            badge = '<span class="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">Enlazado 🔗</span>'
        else:
            badge = '<span class="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">Nuevo 🌟</span>'
        
        # Guardar en DB
        detail = PurchaseOrderDetail(
            purchase_order_id=order.id,
            producto_id=db_product_id,
            nombre_factura=d.nombre_producto,
            cantidad=d.cantidad,
            costo_unitario=d.costo_unitario
        )
        session.add(detail)
        detail_id = detail.id  # necesitamos el id para el form (se asigna al hacer flush arriba)

        precio_caja_val = int(d.sugerencia_nuevo_precio) if d.sugerencia_nuevo_precio else ""
        precio_unidad_val = int(d.sugerencia_precio_unidad) if d.sugerencia_precio_unidad else ""

        margen_inicial = ""
        if d.costo_unitario > 0 and d.sugerencia_nuevo_precio and float(d.sugerencia_nuevo_precio) > 0:
            margen_inicial = round((1 - (float(d.costo_unitario) / float(d.sugerencia_nuevo_precio))) * 100, 1)

        is_med = d.es_medicamento
        is_multipack = not is_med and d.unidades_por_caja > 1
        
        # Add visual tag for medication or multipack
        if is_med:
            badge += ' <span class="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded-full" title="Identificado Automáticamente como Medicamento">💊 Med</span>'
        elif is_multipack:
            badge += ' <span class="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full" title="Identificado y Desempacado Automáticamente">📦 Auto-Multipack</span>'

        # Conditional columns: If NOT a medication, do not allow dividing into pills/tablets
        if is_med or is_multipack:
            unidades_html = f"""
            <td class="p-3">
                <input type="number" 
                       name="unidades_{idx}" 
                       value="{d.unidades_por_caja}" min="1"
                       class="w-20 text-center border-2 border-gray-100 rounded-lg px-2 py-1.5 text-sm font-bold focus:border-indigo-400 focus:outline-none transition-colors bg-gray-50 bg-white"
                       onchange="recalcUnit(this, {idx})"
                       title="¿Cuántos sobres/unidades trae cada caja?">
            </td>
            """
            
            precio_unidad_html = f"""
            <td class="p-3">
                <div class="relative">
                    <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm font-bold">$</span>
                    <input type="number" 
                           name="precio_unidad_{idx}" 
                           id="precio_unidad_{idx}"
                           value="{precio_unidad_val}"
                           class="w-28 pl-6 border-2 border-green-100 rounded-lg px-2 py-1.5 text-sm font-black text-green-700 focus:border-green-400 focus:outline-none transition-colors bg-green-50 focus:bg-white"
                           step="50"
                           onchange="snapToCOP(this); recalcBoxFromUnit(this, {idx})"
                           title="Precio de venta por sobre/unidad individual">
                </div>
            </td>
            """
        else:
            unidades_html = f"""
            <td class="p-3 text-center align-middle">
                <button type="button" onclick="enableMultipack(event, {idx})" class="mt-1 text-[11px] uppercase tracking-wider text-indigo-500 hover:text-indigo-700 font-bold bg-indigo-50 hover:bg-indigo-100 px-2 py-1 rounded transition-colors border border-indigo-100">Desempacar</button>
                <div id="unid_wrapper_{idx}" class="hidden">
                    <input type="number" 
                           name="unidades_{idx}" 
                           value="1" min="1"
                           class="w-20 text-center border-2 border-gray-100 rounded-lg px-2 py-1.5 text-sm font-bold focus:border-indigo-400 focus:outline-none transition-colors bg-white mt-1"
                           onchange="recalcUnit(this, {idx})"
                           title="¿Cuántas unidades trae cada caja?">
                </div>
            </td>
            """
            
            precio_unidad_html = f"""
            <td class="p-3 text-center align-middle">
                <span class="block mt-2 text-gray-400 text-xs italic font-semibold cursor-not-allowed" id="punid_na_{idx}" title="No aplica para este producto">N/A</span>
                <div id="punid_wrapper_{idx}" class="relative hidden mt-1">
                    <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm font-bold">$</span>
                    <input type="number" 
                           name="precio_unidad_{idx}" 
                           id="precio_unidad_{idx}"
                           value="{precio_caja_val}"
                           class="w-28 pl-6 border-2 border-green-100 rounded-lg px-2 py-1.5 text-sm font-black text-green-700 focus:border-green-400 focus:outline-none transition-colors bg-green-50 focus:bg-white"
                           step="50"
                           onchange="snapToCOP(this); recalcBoxFromUnit(this, {idx})"
                           title="Precio de venta por unidad individual">
                </div>
            </td>
            """

        # Cada fila tiene inputs del form de confirmación (mismo form más abajo)
        filas_html += f"""
        <tr class="{tr_class} border-b border-gray-100 align-top hover:bg-gray-50 transition-colors" id="row-{idx}">
            <td class="p-3">
                <div class="font-semibold text-gray-900 text-sm">{d.nombre_producto}</div>
                <div class="flex flex-wrap gap-1 mt-1" id="badges_{idx}">{badge} {alerta_subida}</div>
                <input type="hidden" name="nombre_{idx}" value="{d.nombre_producto}">
                <input type="hidden" name="producto_id_{idx}" value="{db_product_id or ''}">
            </td>
            <td class="p-3 text-center text-sm font-bold text-indigo-600">{d.cantidad}</td>
            <td class="p-3 text-center text-sm text-gray-500">${int(d.costo_unitario):,}</td>
            
            <!-- Unidades por caja (editable o N/A según AI) -->
            {unidades_html}
            
            <!-- MARGEN DE GANANCIA (editable) -->
            <td class="p-3">
                <div class="relative">
                    <input type="number" 
                           name="margen_{idx}" 
                           id="margen_{idx}"
                           value="{margen_inicial}"
                           class="w-24 pr-5 border-2 { 'border-red-400 bg-red-50 text-red-700' if margen_inicial and float(margen_inicial) < 0 else 'border-orange-100 bg-orange-50 text-orange-700' } rounded-lg px-2 py-1.5 text-sm font-black focus:border-orange-400 focus:outline-none transition-colors focus:bg-white text-right"
                           step="0.1"
                           onchange="recalcPriceFromMargin(this, {idx})"
                           title="Porcentaje libre de ganancia sobre el costo (Editable)">
                    <span class="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm font-bold">%</span>
                    <input type="hidden" id="costo_{idx}" value="{int(d.costo_unitario)}">
                </div>
            </td>
            
            <!-- Precio por CAJA (editable, con COP rounding) -->
            <td class="p-3">
                <div class="relative">
                    <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm font-bold">$</span>
                    <input type="number" 
                           name="precio_caja_{idx}" 
                           id="precio_caja_{idx}"
                           value="{precio_caja_val}"
                           class="w-32 pl-6 border-2 border-indigo-100 rounded-lg px-2 py-1.5 text-sm font-black text-indigo-700 focus:border-indigo-400 focus:outline-none transition-colors bg-indigo-50 focus:bg-white"
                           step="50"
                           onchange="snapToCOP(this); recalcUnit(this, {idx}); recalcMarginFromPrice(this, {idx})"
                           title="{"Precio de venta por caja completa" if is_med else "Precio de venta sugerido"}">
                </div>
            </td>
            
            <!-- Precio por UNIDAD (calculado automáticamente o N/A) -->
            {precio_unidad_html}
        </tr>
        """
        
    await session.commit()
    
    # JS para recalcular precio por unidad cuando cambia el precio por caja o cantidad de unidades
    js_helpers = """
    <script>
    function snapToCOP(input) {
        const v = parseInt(input.value);
        if (isNaN(v) || v <= 0) return;
        let snapped;
        if (v < 1000)       snapped = Math.round(v / 50) * 50;
        else if (v < 5000)  snapped = Math.round(v / 100) * 100;
        else if (v < 20000) snapped = Math.round(v / 500) * 500;
        else                snapped = Math.round(v / 1000) * 1000;
        input.value = snapped;
    }
    
    function recalcUnit(trigger, idx) {
        const cajaPrecio = parseFloat(document.getElementById('precio_caja_' + idx).value) || 0;
        const unidadesInput = document.querySelector(`input[name="unidades_${idx}"]`);
        const unidades = parseInt(unidadesInput.value) || 1;
        const unidadPrecio = cajaPrecio / unidades;
        const snapped = snapToCOPVal(unidadPrecio);
        document.getElementById('precio_unidad_' + idx).value = snapped;
    }
    
    function snapToCOPVal(v) {
        if (isNaN(v) || v <= 0) return 0;
        if (v < 1000)       return Math.round(v / 50) * 50;
        if (v < 5000)       return Math.round(v / 100) * 100;
        if (v < 20000)      return Math.round(v / 500) * 500;
        return Math.round(v / 1000) * 1000;
    }
    
    function setMarginStyling(inputElement, marginValue) {
        if (marginValue < 0) {
            inputElement.classList.remove('text-orange-700', 'bg-orange-50', 'border-orange-100');
            inputElement.classList.add('text-red-700', 'bg-red-50', 'border-red-400');
        } else {
            inputElement.classList.add('text-orange-700', 'bg-orange-50', 'border-orange-100');
            inputElement.classList.remove('text-red-700', 'bg-red-50', 'border-red-400');
        }
    }

    function recalcPriceFromMargin(trigger, idx) {
        const margen = parseFloat(trigger.value) || 0;
        const costo = parseFloat(document.getElementById('costo_' + idx).value) || 0;
        
        // Prevent 100% margin (div by 0) or weird inputs, but negative is allowed
        if (margen >= 100) return;
        
        const nuevoPrecio = costo / (1 - (margen / 100));
        const snapped = snapToCOPVal(nuevoPrecio);
        
        const precioCajaInput = document.getElementById('precio_caja_' + idx);
        precioCajaInput.value = snapped;
        
        setMarginStyling(trigger, margen);
        
        // Propagate to unit price
        recalcUnit(null, idx);
    }
    
    function recalcMarginFromPrice(trigger, idx) {
        const precio = parseFloat(trigger.value) || 0;
        const costo = parseFloat(document.getElementById('costo_' + idx).value) || 0;
        
        if (precio <= 0 || costo <= 0) return;
        
        const margen = (1 - (costo / precio)) * 100;
        const margenInput = document.getElementById('margen_' + idx);
        margenInput.value = margen.toFixed(1);
        
        setMarginStyling(margenInput, margen);
    }
    
    function recalcBoxFromUnit(trigger, idx) {
        const unitPrecio = parseFloat(trigger.value) || 0;
        const unidadesInput = document.querySelector(`input[name="unidades_${idx}"]`);
        const unidades = parseInt(unidadesInput.value) || 1;
        const cajaPrecio = unitPrecio * unidades;
        const snapped = snapToCOPVal(cajaPrecio);
        
        const precioCajaInput = document.getElementById('precio_caja_' + idx);
        precioCajaInput.value = snapped;
        
        // Update margin based on new box price
        recalcMarginFromPrice(precioCajaInput, idx);
    }
    
    function enableMultipack(event, idx) {
        document.getElementById('unid_wrapper_' + idx).classList.remove('hidden');
        document.getElementById('punid_wrapper_' + idx).classList.remove('hidden');
        document.getElementById('punid_na_' + idx).classList.add('hidden');
        
        event.target.classList.add('hidden');
        
        const badgeContainer = document.getElementById('badges_' + idx);
        if (badgeContainer) {
             badgeContainer.insertAdjacentHTML('beforeend', '<span class="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full" title="Marcado manualmente como Multipack para venta por unidad">📦 Multipack</span>');
        }
    }
    </script>
    """
    
    html = f"""
    {js_helpers}
    <div id="preview-container" class="bg-white p-6 rounded-2xl shadow border border-gray-100 mb-8">
        <!-- Encabezado -->
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
            <div>
                <h3 class="text-2xl font-black text-gray-900">Pre-Visualización de Factura</h3>
                <p class="text-gray-500 text-sm mt-1">Proveedor: <strong>{parsed_invoice.proveedor_nombre}</strong> · NIT: {parsed_invoice.proveedor_nit}</p>
                <p class="text-gray-400 text-xs">N° Factura: <strong class="text-indigo-600">{parsed_invoice.numero_factura}</strong></p>
            </div>
            <div class="p-3 bg-blue-50 rounded-xl text-xs text-blue-800 max-w-sm leading-relaxed">
                💡 <strong>Tip:</strong> Cambia los precios directamente en la tabla. El precio por sobre/unidad se calcula automáticamente al dividir el precio por caja.
                Los valores se redondean automáticamente a denominaciones colombianas válidas.
            </div>
        </div>
        
        <!-- Formulario editable que envía todo -->
        <form hx-post="/api/v1/purchases/confirm/{order.id}" hx-target="#preview-container" hx-swap="outerHTML">
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead>
                        <tr class="bg-gray-50 text-gray-500 uppercase text-xs border-b-2 border-gray-100">
                            <th class="p-3">Producto</th>
                            <th class="p-3 text-center">Cajas</th>
                            <th class="p-3 text-center">Costo/Caja</th>
                            <th class="p-3 text-center">Unid./Caja 
                                <span class="normal-case text-gray-400 font-normal">(sobres)</span>
                            </th>
                            <th class="p-3 text-center text-orange-600">% Margen ✏️</th>
                            <th class="p-3 text-center text-indigo-600">Precio Venta/Caja ✏️</th>
                            <th class="p-3 text-center text-green-600">Precio/Unidad ✏️</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filas_html}
                    </tbody>
                </table>
            </div>
            
            <input type="hidden" name="total_items" value="{len(parsed_invoice.detalles)}">
            
            <div class="flex justify-end mt-6 pt-4 border-t border-gray-100">
                <button type="submit"
                    class="bg-green-600 hover:bg-green-700 active:scale-95 text-white font-bold py-3 px-8 rounded-xl shadow-lg transition-all flex items-center gap-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                    Confirmar Ingesta y Sumar Stock
                </button>
            </div>
        </form>
    </div>
    """
    
    return HTMLResponse(content=html)


@router.post("/confirm/{order_id}", response_class=HTMLResponse)
async def confirm_ingesta(order_id: uuid.UUID, session: SessionDep):
    """
    Aprueba la ingesta: Suma stock, actualiza costos de compra 
    y aplica los nuevos precios sugeridos al inventario vivo.
    """
    result = await session.execute(select(PurchaseOrder).where(PurchaseOrder.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order or order.estado != PurchaseStatus.DRAFT:
        return HTMLResponse('<div class="text-red-500">Orden inválida o ya procesada.</div>')
    
    # Traer detalles para el procesamiento
    result_details = await session.execute(select(PurchaseOrderDetail).where(PurchaseOrderDetail.purchase_order_id == order.id))
    detalles = result_details.scalars().all()
    
    async with session.begin():
        for det in detalles:
            if det.producto_id:
                # Actualizar el producto existente
                prod_res = await session.execute(select(Product).where(Product.id == det.producto_id))
                prod = prod_res.scalar_one_or_none()
                if prod:
                    prod.stock_actual += det.cantidad
                    
                    # Automágicamente: Si el nuevo stock tiene un costo unitario más alto, subir precio
                    # (Se aplica sugerencia si es mayor estricto al antiguo)
                    margen = 0.35 # Config a futuro
                    if det.costo_unitario > prod.precio_compra:
                        nuevo_precio_venta = det.costo_unitario / Decimal(str(1 - margen))
                        prod.precio_venta = round(nuevo_precio_venta, 2)
                        
                    prod.precio_compra = det.costo_unitario
                    session.add(prod)
            else:
                # Opcional: Crear Nuevo Medicamento Fantasma si no existía (Podemos omitirlo o generarlo sin precio hasta editarlo)
                pass
                
        # Marcar como confirmada
        order.estado = PurchaseStatus.CONFIRMED
        session.add(order)
        
    return HTMLResponse(content=f"""
    <div class="bg-green-100 border-l-4 border-green-500 text-green-900 p-6 rounded-lg shadow animate-fade-in-up">
        <h3 class="font-black text-xl mb-2">¡Inventario Abastecido Exitosamente! 🎉</h3>
        <p>La factura <strong>{order.numero_factura}</strong> de <strong>{order.proveedor.nombre_comercial}</strong> ha sido procesada.</p>
        <p class="font-medium mt-1">El stock se ha sumado y los precios fueron re-ajustados según la regla de márgenes.</p>
        <button onclick="window.location.reload()" class="mt-4 bg-white text-green-700 px-4 py-2 font-bold rounded shadow-sm border border-green-200 hover:bg-green-50 transition-colors">Cargar otra Factura</button>
    </div>
    """)
