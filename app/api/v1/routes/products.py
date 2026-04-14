import uuid
import re
from typing import List
from fastapi import APIRouter, Depends, status, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.dependencies.db import SessionDep
from app.core.catalog_database import search_catalog
from app.services.product_service import ProductService
from app.schemas.product import ProductCreate, ProductUpdate
from app.models.product import Product

router = APIRouter(prefix="/products", tags=["Inventory"])
templates = Jinja2Templates(directory="app/templates")

def get_product_service(session: SessionDep) -> ProductService:
    return ProductService(session)

@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    request: Request,
    service: ProductService = Depends(get_product_service)
):
    # Detectar si es JSON o Form (soporte para HTMX)
    content_type = request.headers.get("Content-Type", "")
    if "application/json" in content_type:
        data_dict = await request.json()
    else:
        form_data = await request.form()
        data_dict = dict(form_data)
    
    try:
        data = ProductCreate(**data_dict)
    except ValidationError as e:
        # Error específico de validación Pydantic
        detail = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=422, detail=detail)
    except (TypeError, KeyError) as e:
        # Error de estructura de datos
        raise HTTPException(status_code=400, detail=f"Estructura de solicitud inválida: {str(e)}")

    return await service.create_product(data)

@router.get("/", response_model=List[Product])
async def list_products(
    skip: int = 0, 
    limit: int = 100, 
    service: ProductService = Depends(get_product_service)
):
    return await service.list_products(skip, limit)

@router.get("/critical", response_model=List[Product])
async def get_critical_stock(
    service: ProductService = Depends(get_product_service)
):
    return await service.list_critical_stock()

@router.patch("/{product_id}", response_model=Product)
async def update_product(
    product_id: uuid.UUID, 
    request: Request,
    service: ProductService = Depends(get_product_service)
):
    # Detectar si es JSON o Form (soporte para HTMX)
    content_type = request.headers.get("Content-Type", "")
    if "application/json" in content_type:
        data_dict = await request.json()
    else:
        form_data = await request.form()
        data_dict = dict(form_data)

    try:
        data = ProductUpdate(**data_dict)
    except ValidationError as e:
        # Error específico de validación Pydantic
        detail = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=422, detail=detail)
    except (TypeError, KeyError) as e:
        # Error de estructura de datos
        raise HTTPException(status_code=400, detail=f"Estructura de solicitud inválida: {str(e)}")

    return await service.update_product(product_id, data)


# --- Rutas HTMX (Server-Side Rendering Partials) ---

@router.get("/inventory-search", response_class=HTMLResponse)
async def visual_inventory_search_page(request: Request):
    """Sirve la página Minimalista de Búsqueda de Inventario."""
    return templates.TemplateResponse(request=request, name="inventory_search.html")


def _extract_units_from_desc(desc: str) -> int:
    """Intenta extraer el número de unidades por caja de la descripción INVIMA."""
    if not desc:
        return 1
    desc = desc.upper()
    # Patrón: "POR 10", "X 30". Evitamos capturar concentraciones (mg, g, ml, etc.)
    matches = re.findall(r"(?:POR|X)\s*(\d+)\s*(?!(?:MG|G|ML|MCG|UI|L)\b)", desc)
    if not matches:
        return 1
    
    # Convertir a lista de enteros ordenados de mayor a menor
    nums = sorted([int(m) for m in matches if int(m) > 0], reverse=True)
    if not nums:
        return 1
    if len(nums) == 1:
        return nums[0]

    # Heurística Avanzada:
    # Caso 1: Redundancia con desglose (ej: 300 unidades de 30 blister por 10)
    # Si el valor máximo es igual al producto de los demás, el máximo es el total.
    max_val = nums[0]
    others = nums[1:]
    prod_others = 1
    for n in others:
        prod_others *= n
    
    if max_val == prod_others:
        return max_val
    
    # Caso 2: Redundancia simple (ej: POR 10... POR 10) o Multiplicación pura (ej: 2 X 10)
    # Multiplicamos los valores únicos encontrados.
    unique_vals = []
    for n in nums:
        if n not in unique_vals:
            unique_vals.append(n)
    
    total = 1
    for v in unique_vals:
        total *= v
    return total


@router.get("/htmx/new-form", response_class=HTMLResponse)
async def htmx_new_product_form(
    request: Request,
    nombre: str = "",
    principio_activo: str = "",
    registro_invima: str = "",
    laboratorio: str = "",
    categoria: str = "",
    descripcion: str = "",
):
    import html as html_mod

    esc = html_mod.escape
    html = f"""
    <div class="max-w-4xl mx-auto bg-white p-8 rounded-3xl shadow-xl border border-gray-100 animate-fade-in">
        <button class="text-gray-400 hover:text-blue-600 flex items-center font-medium transition-colors text-sm mb-6" onclick="window.location.reload()">
            <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
            Volver al buscador
        </button>

        <div class="mb-5">
            <label class="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Buscar por nombre en INVIMA</label>
            <input type="text" name="invima_q" placeholder="Ej: amoxicilina 500"
                   hx-get="/api/v1/products/htmx/invima-suggest"
                   hx-trigger="keyup changed delay:300ms"
                   hx-target="#invima-suggest-results"
                   class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-400 outline-none transition-all text-sm">
            <div id="invima-suggest-results" class="mt-2 border border-gray-100 rounded-xl max-h-52 overflow-y-auto"></div>
        </div>

        <form id="new-product-form"
              hx-post="/api/v1/products/"
              hx-swap="none"
              hx-on::after-request="if(event.detail.successful){{alert('Producto registrado'); window.location.reload();}} else {{alert('Error: ' + event.detail.xhr.responseText);}}"
              class="space-y-4">
            <input type="hidden" name="categoria" value="{esc(categoria)}">

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Codigo de Barras *</label>
                    <input type="text" name="codigo_barras" required class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl">
                </div>
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Nombre *</label>
                    <input type="text" name="nombre" value="{esc(nombre)}" required class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl">
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Registro INVIMA *</label>
                    <input type="text" name="registro_invima" value="{esc(registro_invima)}" required class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl">
                </div>
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Marca/Laboratorio *</label>
                    <input type="text" name="marca_laboratorio" value="{esc(laboratorio)}" required class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl">
                    <input type="hidden" name="laboratorio" value="{esc(laboratorio)}">
                </div>
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Principio Activo</label>
                    <input type="text" name="principio_activo" value="{esc(principio_activo)}" class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl">
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Lote *</label>
                    <input type="text" name="lote" required placeholder="Se completa manualmente" class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl">
                </div>
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Fecha Vencimiento *</label>
                    <input type="date" name="fecha_vencimiento" required class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl">
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Costo Caja *</label>
                    <input type="number" step="50" name="costo_caja" id="np-costo-caja" required oninput="npRecalc()" class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl">
                    <input type="hidden" name="precio_compra" id="np-precio-compra">
                </div>
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Unidades por Caja *</label>
                    <input type="number" name="unidades_por_caja" id="np-upc" value="{_extract_units_from_desc(descripcion)}" min="1" required oninput="npRecalc()" class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl">
                </div>
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Margen %</label>
                    <input type="number" name="np-margen" id="np-margen" value="40" min="-90" max="99" oninput="npRecalc()" class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl">
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs font-bold text-emerald-700 uppercase tracking-wider mb-1.5">Precio Venta Unidad *</label>
                    <input type="number" step="50" name="precio_venta_unidad" id="np-pvu" required oninput="npSyncVentaCaja()" class="w-full px-4 py-3 bg-emerald-50 border border-emerald-200 rounded-xl font-bold text-emerald-700">
                </div>
                <div>
                    <label class="block text-xs font-bold text-indigo-700 uppercase tracking-wider mb-1.5">Precio Venta Caja</label>
                    <input type="number" step="50" name="precio_venta" id="np-pvc" class="w-full px-4 py-3 bg-indigo-50 border border-indigo-200 rounded-xl font-bold text-indigo-700">
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Stock Inicial *</label>
                    <input type="number" name="stock_actual" value="0" required class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl">
                </div>
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Stock Minimo *</label>
                    <input type="number" name="stock_minimo" value="5" required class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl">
                </div>
            </div>

            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-xl shadow-lg transition-all">
                Registrar en Inventario
            </button>
        </form>
    </div>

    <script>
        function npSnap(v) {{
            if (!v || v <= 0) return 0;
            if (v < 1000) return Math.round(v / 50) * 50;
            if (v < 5000) return Math.round(v / 100) * 100;
            if (v < 20000) return Math.round(v / 500) * 500;
            return Math.round(v / 1000) * 1000;
        }}
        function npRecalc() {{
            const c = parseFloat(document.getElementById('np-costo-caja').value) || 0;
            const u = Math.max(parseInt(document.getElementById('np-upc').value) || 1, 1);
            const m = parseFloat(document.getElementById('np-margen').value) || 40;
            if (m >= 99) return;
            const pvc = npSnap(c / (1 - (m/100)));
            const pvu = npSnap(pvc / u);
            document.getElementById('np-pvc').value = pvc;
            document.getElementById('np-pvu').value = pvu;
            document.getElementById('np-precio-compra').value = c;
        }}
        function npSyncVentaCaja() {{
            const u = Math.max(parseInt(document.getElementById('np-upc').value) || 1, 1);
            const pvu = parseFloat(document.getElementById('np-pvu').value) || 0;
            document.getElementById('np-pvc').value = npSnap(pvu * u);
        }}
        function applyInvimaSuggestion(nombre, registro, laboratorio, principio) {{
            const nameInput = document.querySelector('input[name="nombre"]');
            const regInput = document.querySelector('input[name="registro_invima"]');
            const labInput = document.querySelector('input[name="marca_laboratorio"]');
            const legacyLab = document.querySelector('input[name="laboratorio"]');
            const paInput = document.querySelector('input[name="principio_activo"]');
            if (nameInput) nameInput.value = nombre || '';
            if (regInput) regInput.value = registro || '';
            if (labInput) labInput.value = laboratorio || '';
            if (legacyLab) legacyLab.value = laboratorio || '';
            if (paInput) paInput.value = principio || '';
            const target = document.getElementById('invima-suggest-results');
            if (target) target.innerHTML = '';
        }}
        npRecalc();
    </script>
    """
    return HTMLResponse(content=html)


@router.get("/htmx/invima-suggest", response_class=HTMLResponse)
async def htmx_invima_suggest(q: str = ""):
    if not q or len(q.strip()) < 2:
        return HTMLResponse(content="")

    results = await search_catalog(q, limit=8)
    if not results:
        return HTMLResponse('<div class="px-3 py-2 text-xs text-gray-400">Sin sugerencias en INVIMA</div>')

    items = ""
    for r in results:
        nombre_r = (r.get("nombre_comercial") or "").replace("'", "\\'")
        reg_r = (r.get("registro_invima") or "").replace("'", "\\'")
        lab_r = (r.get("titular") or "").replace("'", "\\'")
        principio_r = (r.get("principio_activo") or "").replace("'", "\\'")
        items += f"""
        <button type="button" class="w-full text-left px-3 py-2 hover:bg-blue-50 border-b border-gray-100 last:border-0"
                onclick="applyInvimaSuggestion('{nombre_r}','{reg_r}','{lab_r}','{principio_r}')">
            <div class="text-sm font-semibold text-gray-800">{_esc(r.get('nombre_comercial', ''))}</div>
            <div class="text-[11px] text-gray-500">{_esc(r.get('titular', ''))} · {_esc(r.get('registro_invima', ''))}</div>
        </button>
        """
    return HTMLResponse(content=items)


@router.get("/search", response_class=HTMLResponse)
async def htmx_visual_search(
    request: Request,
    q: str = "",
    service: ProductService = Depends(get_product_service)
):
    """
    Retorna Tarjetas HTML (Cards) Visuales con la imagen del producto.
    """
    if not q or len(q) < 2:
        return HTMLResponse(content="")

    products = await service.search_products(q)
    
    if not products:
        return HTMLResponse(content="<div class='col-span-full p-8 text-center text-gray-500 font-medium'>No se encontraron coincidencias</div>")
    
    from app.services.image_service import ImageService
    
    # Construir el grid de tarjetas
    items_html = ""
    for p in products:
        img = p.image_url or ImageService.get_image_for_product(p.nombre)
        items_html += f"""
        <div class="bg-white rounded-2xl shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden border border-gray-100 flex flex-col">
            <img src="{img}" alt="{p.nombre}" class="w-full h-48 object-cover">
            <div class="p-5 flex flex-col flex-grow">
                <h3 class="font-bold text-gray-800 text-lg mb-1">{p.nombre}</h3>
                <p class="text-sm text-gray-400 mb-4">{p.codigo_barras}</p>
                <div class="mt-auto">
                    <button class="w-full bg-blue-50 text-blue-700 hover:bg-blue-600 hover:text-white font-semibold py-3 px-4 rounded-xl transition-colors"
                            hx-get="/api/v1/products/htmx/load-form/{p.id}"
                            hx-target="#main-container"
                            hx-swap="innerHTML">
                        Seleccionar
                    </button>
                </div>
            </div>
        </div>
        """
    return HTMLResponse(content=items_html)

# ─── CATÁLOGO VISUAL (Ver Inventario) ─────────────────────────────────────────

def _build_product_card(p) -> str:
    """Genera el HTML de una tarjeta cuadrada de producto para el catálogo."""
    from app.services.image_service import ImageService
    img = p.image_url or ImageService.get_image_for_product(p.nombre)
    precio = f"${int(p.precio_venta):,}"

    if p.stock_actual == 0:
        stock_badge = '<span class="text-[10px] font-bold bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">Sin stock</span>'
    elif p.stock_actual <= p.stock_minimo:
        stock_badge = f'<span class="text-[10px] font-bold bg-red-100 text-red-700 px-2 py-0.5 rounded-full">Crítico ({p.stock_actual})</span>'
    else:
        stock_badge = f'<span class="text-[10px] font-bold bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">Stock: {p.stock_actual}</span>'

    # Badge de laboratorio (si existe)
    lab_html = ""
    if getattr(p, 'laboratorio', None):
        lab_html = f'<div class="text-[10px] font-black text-blue-600 uppercase tracking-tight mb-0.5 truncate" title="{p.laboratorio}">{p.laboratorio}</div>'
    
    # Badge de INVIMA (opcional)
    invima_html = ""
    if getattr(p, 'registro_invima', None):
        invima_html = f'<div class="text-[9px] text-gray-400 font-mono mt-0.5">{p.registro_invima}</div>'

    return f"""
    <div class="bg-white rounded-2xl shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden border border-gray-100 flex flex-col group" id="card-{p.id}">
        <div class="relative overflow-hidden">
            <img src="{img}" alt="{p.nombre}" class="w-full h-36 object-cover group-hover:scale-105 transition-transform duration-300">
            <!-- Overlay de acciones -->
            <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                <button class="bg-white/90 hover:bg-red-500 hover:text-white text-red-600 rounded-lg p-2 transition-all shadow"
                        title="Eliminar producto"
                        hx-delete="/api/v1/products/{p.id}"
                        hx-target="#card-{p.id}"
                        hx-swap="outerHTML swap:0.3s"
                        hx-confirm="¿Eliminar '{p.nombre}'? Esta acción no se puede deshacer."
                        hx-on::after-request="this.closest('[id^=card-]')?.remove()">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                    </svg>
                </button>
            </div>
        </div>
        <div class="p-3 flex flex-col flex-grow">
            {lab_html}
            <h3 class="font-bold text-gray-800 text-xs leading-snug line-clamp-2" title="{p.nombre}">{p.nombre}</h3>
            {invima_html}
            <div class="mt-auto pt-2 flex items-center justify-between">
                <span class="text-sm font-black text-blue-700">{precio}</span>
                {stock_badge}
            </div>
        </div>
    </div>
    """

@router.get("/catalog", response_class=HTMLResponse)
async def catalog_page(
    request: Request,
    service: ProductService = Depends(get_product_service)
):
    """Vista principal del catálogo visual de inventario."""
    all_products = await service.list_products(0, 1000)
    total = len(all_products)
    critical = sum(1 for p in all_products if 0 < p.stock_actual <= p.stock_minimo)
    zero = sum(1 for p in all_products if p.stock_actual == 0)
    ok = total - critical - zero

    grid_html = "".join(_build_product_card(p) for p in all_products)

    return templates.TemplateResponse(
        request=request,
        name="inventory_catalog.html",
        context={
            "total_products": total,
            "critical_count": critical,
            "ok_count": ok,
            "zero_count": zero,
            "grid_html": grid_html,
        }
    )

@router.get("/catalog-grid", response_class=HTMLResponse)
async def catalog_grid_partial(
    request: Request,
    q: str = "",
    service: ProductService = Depends(get_product_service)
):
    """Partial HTMX: retorna solo las tarjetas filtradas para el catálogo."""
    if q and len(q) >= 2:
        products = await service.search_products(q)
    else:
        products = await service.list_products(0, 1000)

    if not products:
        return HTMLResponse('<div class="col-span-full p-12 text-center text-gray-400">No se encontraron productos.</div>')

    return HTMLResponse("".join(_build_product_card(p) for p in products))


@router.get("/htmx/load-form/{product_id}", response_class=HTMLResponse)
async def htmx_load_form(
    product_id: uuid.UUID,
    service: ProductService = Depends(get_product_service)
):
    """Formulario expandido: modo de ingreso (caja/sobre/unidad) + botón eliminar."""
    p = await service.get_by_id(product_id)
    from app.services.image_service import ImageService
    img = p.image_url or ImageService.get_image_for_product(p.nombre)

    html = f"""
    <div class="max-w-2xl mx-auto bg-white p-8 rounded-3xl shadow-xl animate-fade-in">
        <!-- Cabecera: volver + eliminar -->
        <div class="flex items-center justify-between mb-6">
            <button class="text-gray-400 hover:text-blue-600 flex items-center font-medium transition-colors text-sm"
                    onclick="window.location.reload()">
                <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
                </svg>
                Volver
            </button>
            <button class="flex items-center gap-1.5 text-red-500 hover:text-white hover:bg-red-500 border border-red-200 hover:border-red-500 text-xs font-bold px-3 py-1.5 rounded-lg transition-all"
                    hx-delete="/api/v1/products/{p.id}"
                    hx-confirm="¿Estás seguro de eliminar '{p.nombre}'? Esta acción no se puede deshacer."
                    hx-on::after-request="alert('Producto eliminado'); window.location.reload();">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
                Eliminar producto
            </button>
        </div>

        <!-- Info producto -->
        <div class="flex items-center gap-5 mb-8 p-4 bg-blue-50/60 rounded-2xl border border-blue-100">
            <img src="{img}" class="w-20 h-20 rounded-xl object-cover shadow-sm flex-shrink-0">
            <div>
                <h2 class="text-xl font-bold text-gray-900">{p.nombre}</h2>
                <p class="text-gray-400 text-sm">{p.codigo_barras or 'Sin código de barras'}</p>
                <p class="text-blue-700 font-bold text-sm mt-0.5">Precio venta: ${int(p.precio_venta):,}</p>
            </div>
        </div>

        <!-- Selector de modo de ingreso -->
        <div class="mb-6">
            <label class="block text-xs font-bold text-blue-700 uppercase tracking-wider mb-2">¿Qué vas a ingresar?</label>
            <div class="grid grid-cols-3 gap-2" id="mode-selector">
                <button type="button" onclick="setMode('caja')"
                        id="btn-caja"
                        class="mode-btn active-mode flex flex-col items-center gap-1.5 py-3 px-2 rounded-xl border-2 border-blue-500 bg-blue-50 text-blue-700 font-bold text-xs transition-all">
                    📦<span>Caja Completa</span>
                </button>
                <button type="button" onclick="setMode('sobre')"
                        id="btn-sobre"
                        class="mode-btn flex flex-col items-center gap-1.5 py-3 px-2 rounded-xl border-2 border-gray-200 bg-white text-gray-500 font-bold text-xs transition-all hover:border-blue-300">
                    🗂️<span>Sobres / Blísters</span>
                </button>
                <button type="button" onclick="setMode('unidad')"
                        id="btn-unidad"
                        class="mode-btn flex flex-col items-center gap-1.5 py-3 px-2 rounded-xl border-2 border-gray-200 bg-white text-gray-500 font-bold text-xs transition-all hover:border-blue-300">
                    💊<span>Unidades Sueltas</span>
                </button>
            </div>
            <p id="mode-hint" class="text-xs text-gray-500 mt-2 text-center">Ingresando una <strong>caja completa</strong> de producto.</p>
        </div>

        <!-- Formulario de actualización -->
        <form id="inventory-form" hx-patch="/api/v1/products/{p.id}" hx-swap="none"
              hx-on::after-request="alert('✅ Inventario actualizado!'); window.location.reload();">
            <div class="space-y-5">

                <!-- Cantidad a agregar (dinámica según modo) -->
                <div class="bg-gray-50 rounded-xl p-4 border border-gray-200">
                    <label class="block text-sm font-semibold text-gray-700 mb-2">
                        <span id="qty-label">Número de cajas a ingresar</span>
                        <span class="text-xs font-normal text-gray-400 ml-1">(se sumará al stock actual: {p.stock_actual})</span>
                    </label>
                    <div class="flex items-center gap-3">
                        <button type="button" onclick="adjustQty(-1)"
                                class="w-10 h-10 rounded-lg bg-white border-2 border-gray-200 text-gray-600 font-bold text-xl hover:border-blue-400 hover:text-blue-600 transition-all flex items-center justify-center">−</button>
                        <input type="number" id="qty-input" name="cantidad_ingreso" value="1" min="1"
                               class="flex-1 text-center text-2xl font-black text-blue-700 bg-white border-2 border-blue-200 rounded-xl py-2 focus:ring-2 focus:ring-blue-400 outline-none">
                        <button type="button" onclick="adjustQty(1)"
                                class="w-10 h-10 rounded-lg bg-white border-2 border-gray-200 text-gray-600 font-bold text-xl hover:border-blue-400 hover:text-blue-600 transition-all flex items-center justify-center">+</button>
                    </div>
                    <!-- Unidades por caja (ahora persistente en DB) -->
                    <div id="units-per-box-row" class="mt-3 flex items-center gap-3">
                        <label class="text-xs text-gray-500 whitespace-nowrap">Unidades por caja/sobre:</label>
                        <input type="number" id="units-per-box" name="unidades_por_caja" value="{p.unidades_por_caja}" min="1"
                               class="w-20 text-center border border-blue-200 bg-blue-50 rounded-lg px-2 py-1 text-sm font-bold text-blue-700 focus:border-blue-400 outline-none"
                               onchange="updateStockPreview()">
                    </div>
                    <!-- Vista previa del nuevo stock -->
                    <div class="mt-3 text-center">
                        <span class="text-xs text-emerald-700 font-bold bg-emerald-50 px-3 py-1 rounded-full">
                            Stock resultante: <span id="stock-preview">{p.stock_actual + 1}</span> unidades
                        </span>
                    </div>
                    <input type="hidden" name="stock_actual" id="stock-final" value="{p.stock_actual + 1}">
                </div>

                <!-- Precios -->
                <div class="space-y-3">
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-2">Precio Compra ($)</label>
                            <input type="number" step="50" name="precio_compra" id="precio-compra"
                                   value="{int(p.precio_compra)}" required
                                   oninput="recalcVentaIfAuto()"
                                   class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-400 focus:border-transparent outline-none transition-all font-bold">
                        </div>
                        <div>
                            <label class="block text-sm font-semibold text-gray-700 mb-2">Precio Venta ($)</label>
                            <input type="number" step="50" name="precio_venta" id="precio-venta"
                                   value="{int(p.precio_venta)}" required
                                   oninput="clearAutoMode()"
                                   class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-400 focus:border-transparent outline-none transition-all font-bold text-blue-700">
                        </div>
                    </div>
                    <!-- Botones de margen automático -->
                    <div class="flex items-center gap-2">
                        <span class="text-xs text-gray-400 font-semibold whitespace-nowrap">Auto-precio:</span>
                        <div class="flex gap-1.5 flex-wrap">
                            <button type="button" onclick="applyMargin(0.20)" id="margin-btn-20"
                                    class="margin-btn px-2.5 py-1 rounded-lg text-xs font-bold border-2 border-gray-200 text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-all">
                                20%
                            </button>
                            <button type="button" onclick="applyMargin(0.30)" id="margin-btn-30"
                                    class="margin-btn px-2.5 py-1 rounded-lg text-xs font-bold border-2 border-gray-200 text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-all">
                                30%
                            </button>
                            <button type="button" onclick="applyMargin(0.40)" id="margin-btn-40"
                                    class="margin-btn px-2.5 py-1 rounded-lg text-xs font-bold border-2 border-blue-500 bg-blue-50 text-blue-700 transition-all">
                                40% ✓
                            </button>
                            <button type="button" onclick="applyMargin(0.50)" id="margin-btn-50"
                                    class="margin-btn px-2.5 py-1 rounded-lg text-xs font-bold border-2 border-gray-200 text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-all">
                                50%
                            </button>
                            <button type="button" onclick="applyMargin(0.75)" id="margin-btn-75"
                                    class="margin-btn px-2.5 py-1 rounded-lg text-xs font-bold border-2 border-gray-200 text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-all">
                                75%
                            </button>
                        </div>
                        <span id="margin-label" class="text-xs text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded-full hidden"></span>
                    </div>
                </div>


                <!-- Stock mínimo -->
                <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-2">Alerta de Stock Mínimo</label>
                    <input type="number" name="stock_minimo" value="{p.stock_minimo}" required
                           class="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-400 focus:border-transparent outline-none transition-all">
                </div>
            </div>

            <button type="submit"
                    class="mt-6 w-full bg-blue-600 hover:bg-blue-700 active:scale-95 text-white font-bold py-4 rounded-xl shadow transition-all">
                Guardar en Inventario
            </button>
        </form>
    </div>

    <style>
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .animate-fade-in {{ animation: fadeIn 0.3s ease-out forwards; }}
        .active-mode {{ border-color: #2563eb !important; background-color: #eff6ff !important; color: #1d4ed8 !important; }}
    </style>

    <script>
        const CURRENT_STOCK = {p.stock_actual};
        let currentMode = 'caja';

        const hints = {{
            caja:   'Ingresando una <strong>caja completa</strong> de producto. El sistema multiplicará × unidades por caja.',
            sobre:  'Ingresando <strong>sobres o blísters</strong> individuales.',
            unidad: 'Ingresando <strong>unidades sueltas</strong> (pastillas, comprimidos, etc.).'
        }};
        const labels = {{
            caja:  'Número de cajas a ingresar',
            sobre: 'Número de sobres/blísters a ingresar',
            unidad:'Número de unidades (pastillas) a ingresar'
        }};

        function setMode(mode) {{
            currentMode = mode;
            ['caja','sobre','unidad'].forEach(m => {{
                document.getElementById('btn-' + m).classList.toggle('active-mode', m === mode);
            }});
            document.getElementById('mode-hint').innerHTML = hints[mode];
            document.getElementById('qty-label').textContent = labels[mode];
            document.getElementById('units-per-box-row').style.display = (mode === 'unidad') ? 'none' : 'flex';
            updateStockPreview();
        }}

        function adjustQty(delta) {{
            const input = document.getElementById('qty-input');
            input.value = Math.max(1, parseInt(input.value || 1) + delta);
            updateStockPreview();
        }}

        function updateStockPreview() {{
            const qty = parseInt(document.getElementById('qty-input').value) || 1;
            const upb = parseInt(document.getElementById('units-per-box').value) || 1;
            let added = (currentMode === 'unidad') ? qty : qty * upb;
            const total = CURRENT_STOCK + added;
            document.getElementById('stock-preview').textContent = total;
            document.getElementById('stock-final').value = total;
        }}

        document.getElementById('qty-input').addEventListener('input', updateStockPreview);
        updateStockPreview();

        // ── Auto-Precio ──────────────────────────────────────────
        let activeMargin = 0.40;

        function snapCOP(v) {{
            if (v < 1000)  return Math.round(v / 50) * 50;
            if (v < 5000)  return Math.round(v / 100) * 100;
            if (v < 20000) return Math.round(v / 500) * 500;
            return Math.round(v / 1000) * 1000;
        }}

        function applyMargin(margin) {{
            activeMargin = margin;
            const costo = parseFloat(document.getElementById('precio-compra').value) || 0;
            if (costo > 0) {{
                const venta = snapCOP(costo / (1 - margin));
                document.getElementById('precio-venta').value = venta;
            }}
            // Visual: highlight active button
            document.querySelectorAll('.margin-btn').forEach(btn => {{
                btn.classList.remove('border-blue-500','bg-blue-50','text-blue-700');
                btn.classList.add('border-gray-200','text-gray-500');
                btn.textContent = btn.textContent.replace(' ✓','');
            }});
            const pct = Math.round(margin * 100);
            const activeBtn = document.getElementById('margin-btn-' + pct);
            if (activeBtn) {{
                activeBtn.classList.add('border-blue-500','bg-blue-50','text-blue-700');
                activeBtn.classList.remove('border-gray-200','text-gray-500');
                activeBtn.textContent = pct + '% ✓';
            }}
            const label = document.getElementById('margin-label');
            if (costo > 0) {{
                label.textContent = '+' + pct + '% margen aplicado';
                label.classList.remove('hidden');
            }}
        }}

        function recalcVentaIfAuto() {{
            if (activeMargin) applyMargin(activeMargin);
        }}

        function clearAutoMode() {{
            activeMargin = null;
            document.getElementById('margin-label').classList.add('hidden');
            document.querySelectorAll('.margin-btn').forEach(btn => {{
                btn.classList.remove('border-blue-500','bg-blue-50','text-blue-700');
                btn.classList.add('border-gray-200','text-gray-500');
                btn.textContent = btn.textContent.replace(' ✓','');
            }});
        }}

        // Aplica automáticamente 40% al cargar
        applyMargin(0.40);
    </script>
    """
    return HTMLResponse(content=html)


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: uuid.UUID,
    service: ProductService = Depends(get_product_service)
):
    """Soft-delete de un producto por ID."""
    await service.delete_product(product_id)


@router.get("/htmx/search", response_class=HTMLResponse)
async def htmx_search_product(
    request: Request,
    codigo_barras: str,
    service: ProductService = Depends(get_product_service)
):
    """Retorna un fragmento HTML de la fila de un producto buscado."""
    product = await service.get_by_codigo(codigo_barras)

    if not product:
        return "<tr class='text-red-500'><td colspan='5' class='px-6 py-4'>Producto no encontrado</td></tr>"

    html_content = f"""
    <tr class="border-b hover:bg-gray-50 transition-colors" id="product-{product.id}">
        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{product.codigo_barras}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{product.nombre}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${product.precio_venta}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm font-bold {'text-red-600' if product.stock_actual <= product.stock_minimo else 'text-emerald-600'}">
            {product.stock_actual}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
            <button class="text-blue-600 hover:text-blue-900" hx-trigger="click">Ver/Editar</button>
        </td>
    </tr>
    """
    return HTMLResponse(content=html_content)
