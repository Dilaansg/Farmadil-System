import hashlib
import html as html_module
import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from lxml import etree
from sqlmodel import select

from app.dependencies.db import SessionDep
from app.models.product import Product
from app.models.purchase import PurchaseOrder, PurchaseOrderDetail, PurchaseStatus, Supplier
from app.schemas.product import ProductCreate
from app.services.parser_service import ParserService
from app.services.product_service import ProductService

router = APIRouter(prefix="/purchases", tags=["Compras e Ingesta"])
templates = Jinja2Templates(directory="app/templates")


def _esc(text: str) -> str:
    return html_module.escape(str(text)) if text is not None else ""


def _round_cop(value: Decimal) -> int:
    v = int(value)
    if v < 1000:
        return int(round(v / 50) * 50)
    if v < 5000:
        return int(round(v / 100) * 100)
    if v < 20000:
        return int(round(v / 500) * 500)
    return int(round(v / 1000) * 1000)


def _parse_date_or_none(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


@router.get("/ingesta", response_class=HTMLResponse)
async def ingesta_page(request: Request):
    return templates.TemplateResponse(request=request, name="ingesta_factura.html")


@router.post("/htmx/recalc-row", response_class=HTMLResponse)
async def recalc_row(request: Request):
    form = await request.form()
    idx_raw = form.get("idx")
    if idx_raw is None:
        for key in form.keys():
            if key.startswith("idx_"):
                idx_raw = str(form.get(key))
                break
    idx = int(str(idx_raw or 0))

    try:
        costo_caja = Decimal(str(form.get(f"costo_caja_{idx}", "0") or "0"))
    except Exception:
        costo_caja = Decimal("0")
    try:
        unidades = max(int(str(form.get(f"unidades_por_caja_{idx}", "1") or "1")), 1)
    except ValueError:
        unidades = 1
    try:
        margen = float(str(form.get(f"margen_{idx}", "40") or "40"))
    except ValueError:
        margen = 40.0

    margen = min(max(margen, -90.0), 99.0)
    sugerido_caja = costo_caja if margen == 100 else (costo_caja / Decimal(str(1 - margen / 100)))
    sugerido_unidad = sugerido_caja / Decimal(str(unidades))

    html = f"""
    <div id="price-preview-{idx}" class="grid grid-cols-2 gap-2">
        <div>
            <label class="block text-[11px] text-indigo-700 font-bold mb-1">Precio sugerido por caja</label>
            <input type="number" name="precio_caja_{idx}" id="precio_caja_{idx}" value="{_round_cop(sugerido_caja)}"
                   class="w-full rounded-lg border border-indigo-200 px-3 py-2 text-sm font-bold text-indigo-700 bg-indigo-50">
        </div>
        <div>
            <label class="block text-[11px] text-emerald-700 font-bold mb-1">Precio sugerido por unidad</label>
            <input type="number" name="precio_unidad_{idx}" id="precio_unidad_{idx}" value="{_round_cop(sugerido_unidad)}"
                   class="w-full rounded-lg border border-emerald-200 px-3 py-2 text-sm font-bold text-emerald-700 bg-emerald-50">
        </div>
    </div>
    """
    return HTMLResponse(html)


@router.post("/preview", response_class=HTMLResponse)
async def preview_invoice(
    session: SessionDep,
    file: UploadFile = File(...),
    margen_configurado: float = Form(0.40),
):
    contents = await file.read()
    filename = (file.filename or "").lower()

    try:
        if filename.endswith(".xlsx"):
            parsed_invoice = ParserService.parse_xlsx(contents)
        elif filename.endswith(".xml"):
            parsed_invoice = ParserService.parse_ubl_xml(contents)
        else:
            return HTMLResponse('<div class="text-red-700 bg-red-100 p-4 rounded-lg">Formato no soportado. Usa .xml o .xlsx.</div>')
    except etree.XMLSyntaxError:
        return HTMLResponse('<div class="text-red-700 bg-red-100 p-4 rounded-lg">El XML tiene errores de estructura.</div>')
    except ValueError as exc:
        return HTMLResponse(f'<div class="text-red-700 bg-red-100 p-4 rounded-lg">No se pudo interpretar la factura: {_esc(str(exc))}</div>')
    except Exception as exc:
        return HTMLResponse(f'<div class="text-red-700 bg-red-100 p-4 rounded-lg">Error inesperado parseando factura: {_esc(str(exc))}</div>')

    result = await session.execute(select(Product).where(Product.is_deleted == False))
    products_db = {p.nombre.lower(): p for p in result.scalars().all()}

    parsed_invoice = ParserService.calculate_price_suggestions(
        parsed_invoice=parsed_invoice,
        db_products=products_db,
        margen_porcentual=margen_configurado,
    )

    for d in parsed_invoice.detalles:
        invima = await ParserService.match_with_invima(d.nombre_producto)
        if invima:
            d.registro_invima_sugerido = invima.get("registro_invima")
            d.principio_activo_sugerido = invima.get("principio_activo")
            d.marca_laboratorio_sugerida = invima.get("marca_laboratorio")
        if not d.marca_laboratorio_sugerida:
            d.marca_laboratorio_sugerida = ParserService.extract_brand_from_invoice_text(d.nombre_producto)

    sup_result = await session.execute(select(Supplier).where(Supplier.nit == parsed_invoice.proveedor_nit))
    supplier = sup_result.scalar_one_or_none()
    if not supplier:
        supplier = Supplier(nit=parsed_invoice.proveedor_nit, nombre_comercial=parsed_invoice.proveedor_nombre)
        session.add(supplier)
        await session.flush()

    monto_total = sum(d.cantidad * d.costo_unitario for d in parsed_invoice.detalles)
    order = PurchaseOrder(
        supplier_id=supplier.id,
        numero_factura=parsed_invoice.numero_factura,
        estado=PurchaseStatus.DRAFT,
        monto_total=monto_total,
    )
    session.add(order)
    await session.flush()

    rows_html = ""
    for idx, d in enumerate(parsed_invoice.detalles):
        matched = products_db.get(d.nombre_producto.lower())
        detail = PurchaseOrderDetail(
            purchase_order_id=order.id,
            producto_id=matched.id if matched else None,
            nombre_factura=d.nombre_producto,
            cantidad=d.cantidad,
            costo_unitario=d.costo_unitario,
        )
        session.add(detail)
        await session.flush()

        sug_caja = _round_cop(d.sugerencia_nuevo_precio or d.costo_unitario)
        sug_unidad = _round_cop(d.sugerencia_precio_unidad or (d.costo_unitario / Decimal(str(max(d.unidades_por_caja, 1)))))
        margin_pct = int(margen_configurado * 100)
        invima = _esc(d.registro_invima_sugerido or "")
        principio = _esc(d.principio_activo_sugerido or "")
        marca = _esc(d.marca_laboratorio_sugerida or "")

        rows_html += f"""
        <tr class="border-b border-gray-100" id="row-{idx}">
            <td class="p-3 align-top">
                <div class="font-semibold text-gray-900 text-sm">{_esc(d.nombre_producto)}</div>
                <div class="text-[11px] text-gray-500">Cant. cajas: {d.cantidad}</div>
                <div class="text-[11px] text-blue-700">INVIMA sugerido: {invima or 'Sin sugerencia'}</div>
                <div class="text-[11px] text-gray-500">Principio activo: {principio or 'N/D'}</div>
                <input type="hidden" name="detail_id_{idx}" value="{detail.id}">
                <input type="hidden" name="idx_{idx}" value="{idx}">
                <input type="hidden" name="nombre_{idx}" value="{_esc(d.nombre_producto)}">
                <input type="hidden" name="cantidad_{idx}" value="{d.cantidad}">
            </td>
            <td class="p-3 align-top">
                <input type="text" name="lote_{idx}" required placeholder="Lote"
                       class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
            </td>
            <td class="p-3 align-top">
                <input type="date" name="fecha_vencimiento_{idx}" required
                       class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
            </td>
            <td class="p-3 align-top">
                <input type="text" name="marca_laboratorio_{idx}" value="{marca}" required
                       class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <input type="text" name="registro_invima_{idx}" value="{invima}" required
                       class="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="Registro INVIMA">
                <input type="text" name="principio_activo_{idx}" value="{principio}"
                       class="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="Principio activo">
            </td>
            <td class="p-3 align-top">
                  <input type="hidden" name="idx_{idx}" value="{idx}">
                <input type="number" name="costo_caja_{idx}" value="{int(d.costo_unitario)}" min="1"
                       hx-post="/api/v1/purchases/htmx/recalc-row"
                       hx-trigger="change"
                       hx-target="#price-preview-{idx}"
                       hx-swap="outerHTML"
                      hx-include="[name='idx_{idx}'],[name='costo_caja_{idx}'],[name='margen_{idx}'],[name='unidades_por_caja_{idx}']"
                       class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm mb-2">
                <input type="number" name="margen_{idx}" value="{margin_pct}" min="-90" max="99"
                       hx-post="/api/v1/purchases/htmx/recalc-row"
                       hx-trigger="change"
                       hx-target="#price-preview-{idx}"
                       hx-swap="outerHTML"
                      hx-include="[name='idx_{idx}'],[name='costo_caja_{idx}'],[name='margen_{idx}'],[name='unidades_por_caja_{idx}']"
                       class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm mb-2" placeholder="Margen %">
                <input type="number" name="unidades_por_caja_{idx}" value="{max(d.unidades_por_caja, 1)}" min="1"
                       hx-post="/api/v1/purchases/htmx/recalc-row"
                       hx-trigger="change"
                       hx-target="#price-preview-{idx}"
                       hx-swap="outerHTML"
                      hx-include="[name='idx_{idx}'],[name='costo_caja_{idx}'],[name='margen_{idx}'],[name='unidades_por_caja_{idx}']"
                       class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="Unid/caja">
                <div id="price-preview-{idx}" class="grid grid-cols-2 gap-2 mt-2">
                    <div>
                        <label class="block text-[11px] text-indigo-700 font-bold mb-1">Precio sugerido por caja</label>
                        <input type="number" name="precio_caja_{idx}" id="precio_caja_{idx}" value="{sug_caja}"
                               class="w-full rounded-lg border border-indigo-200 px-3 py-2 text-sm font-bold text-indigo-700 bg-indigo-50">
                    </div>
                    <div>
                        <label class="block text-[11px] text-emerald-700 font-bold mb-1">Precio sugerido por unidad</label>
                        <input type="number" name="precio_unidad_{idx}" id="precio_unidad_{idx}" value="{sug_unidad}"
                               class="w-full rounded-lg border border-emerald-200 px-3 py-2 text-sm font-bold text-emerald-700 bg-emerald-50">
                    </div>
                </div>
            </td>
        </tr>
        """

    await session.commit()

    html = f"""
    <div id="preview-container" class="bg-white p-6 rounded-2xl shadow border border-gray-100 mb-8">
        <div class="mb-6">
            <h3 class="text-2xl font-black text-gray-900">Pre-visualización inteligente</h3>
            <p class="text-sm text-gray-600">Proveedor: <strong>{_esc(parsed_invoice.proveedor_nombre)}</strong> · Factura: <strong>{_esc(parsed_invoice.numero_factura)}</strong></p>
        </div>

        <form hx-post="/api/v1/purchases/confirm/{order.id}" hx-target="#preview-container" hx-swap="outerHTML">
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead>
                        <tr class="bg-gray-50 text-xs uppercase text-gray-500 border-b border-gray-200">
                            <th class="p-3">Producto</th>
                            <th class="p-3">Lote</th>
                            <th class="p-3">Vencimiento</th>
                            <th class="p-3">INVIMA / Laboratorio</th>
                            <th class="p-3">Costo, Margen y Precio</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>

            <input type="hidden" name="total_items" value="{len(parsed_invoice.detalles)}">
            <div class="flex justify-end mt-6 border-t border-gray-100 pt-4">
                <button type="submit" class="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-6 py-3 rounded-xl transition-colors">
                    Confirmar ingreso de mercancía
                </button>
            </div>
        </form>
    </div>
    """
    return HTMLResponse(content=html)


@router.post("/confirm/{order_id}", response_class=HTMLResponse)
async def confirm_ingesta(order_id: uuid.UUID, request: Request, session: SessionDep):
    result = await session.execute(select(PurchaseOrder).where(PurchaseOrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order or order.estado != PurchaseStatus.DRAFT:
        return HTMLResponse('<div class="text-red-700 bg-red-100 p-4 rounded-lg">Orden inválida o ya procesada.</div>')

    form = await request.form()
    total_items = int(str(form.get("total_items", "0") or "0"))

    details_result = await session.execute(select(PurchaseOrderDetail).where(PurchaseOrderDetail.purchase_order_id == order.id))
    details = {str(d.id): d for d in details_result.scalars().all()}
    if not details:
        return HTMLResponse('<div class="text-red-700 bg-red-100 p-4 rounded-lg">No hay líneas para procesar.</div>')

    auto_mode = total_items <= 0
    product_service = ProductService(session)

    async def _upsert_detail_product(
        detail: PurchaseOrderDetail,
        lote: str,
        fecha_vencimiento: date,
        costo_caja: Decimal,
        unidades_por_caja: int,
        precio_venta_unidad: Decimal,
        marca_laboratorio: str,
        registro_invima: str,
        principio_activo: str | None,
    ) -> None:
        detail.costo_unitario = costo_caja
        session.add(detail)

        qty_added = detail.cantidad * unidades_por_caja
        precio_venta = precio_venta_unidad * unidades_por_caja

        if detail.producto_id:
            prod_res = await session.execute(select(Product).where(Product.id == detail.producto_id))
            product = prod_res.scalar_one_or_none()
            if product:
                product.stock_actual += qty_added
                product.lote = lote
                product.fecha_vencimiento = fecha_vencimiento
                product.marca_laboratorio = marca_laboratorio
                product.registro_invima = registro_invima
                product.principio_activo = principio_activo
                product.costo_caja = costo_caja
                product.unidades_por_caja = unidades_por_caja
                product.precio_venta_unidad = precio_venta_unidad
                product.precio_compra = costo_caja
                product.precio_venta = precio_venta
                product.laboratorio = marca_laboratorio
                session.add(product)
                return

        hash_suffix = hashlib.md5(f"{detail.nombre_factura}-{lote}".encode()).hexdigest()[:10]
        codigo_barras = f"AUTO_{hash_suffix}".upper()

        try:
            new_product = await product_service.create_product(
                ProductCreate(
                    codigo_barras=codigo_barras,
                    nombre=detail.nombre_factura,
                    categoria="Medicamento",
                    lote=lote,
                    fecha_vencimiento=fecha_vencimiento,
                    marca_laboratorio=marca_laboratorio,
                    registro_invima=registro_invima,
                    costo_caja=costo_caja,
                    unidades_por_caja=unidades_por_caja,
                    precio_venta_unidad=precio_venta_unidad,
                    precio_compra=costo_caja,
                    precio_venta=precio_venta,
                    stock_actual=qty_added,
                    stock_minimo=5,
                    principio_activo=principio_activo,
                    laboratorio=marca_laboratorio,
                )
            )
            detail.producto_id = new_product.id
            session.add(detail)
        except Exception:
            existing = await product_service.get_by_codigo(codigo_barras)
            if existing:
                existing.stock_actual += qty_added
                existing.lote = lote
                existing.fecha_vencimiento = fecha_vencimiento
                existing.marca_laboratorio = marca_laboratorio
                existing.registro_invima = registro_invima
                existing.costo_caja = costo_caja
                existing.unidades_por_caja = unidades_por_caja
                existing.precio_venta_unidad = precio_venta_unidad
                existing.precio_compra = costo_caja
                existing.precio_venta = precio_venta
                session.add(existing)

    if auto_mode:
        for detail in details.values():
            await _upsert_detail_product(
                detail=detail,
                lote="PENDIENTE",
                fecha_vencimiento=date(2099, 12, 31),
                costo_caja=detail.costo_unitario,
                unidades_por_caja=1,
                precio_venta_unidad=detail.costo_unitario,
                marca_laboratorio="SIN_MARCA",
                registro_invima="SIN_REGISTRO",
                principio_activo=None,
            )
    else:
        for idx in range(total_items):
            detail_id = str(form.get(f"detail_id_{idx}", "") or "")
            detail = details.get(detail_id)
            if not detail:
                continue

            lote = str(form.get(f"lote_{idx}", "") or "").strip()
            fecha_vencimiento = _parse_date_or_none(str(form.get(f"fecha_vencimiento_{idx}", "") or ""))
            if not lote or not fecha_vencimiento:
                return HTMLResponse(
                    f'<div class="text-red-700 bg-red-100 p-4 rounded-lg">La línea {idx + 1} requiere lote y fecha de vencimiento válidos.</div>'
                )

            costo_caja = Decimal(str(form.get(f"costo_caja_{idx}", "0") or "0"))
            unidades_por_caja = max(int(str(form.get(f"unidades_por_caja_{idx}", "1") or "1")), 1)
            precio_venta_unidad = Decimal(str(form.get(f"precio_unidad_{idx}", "0") or "0"))
            marca_laboratorio = str(form.get(f"marca_laboratorio_{idx}", "") or "").strip() or "SIN_MARCA"
            registro_invima = str(form.get(f"registro_invima_{idx}", "") or "").strip() or "SIN_REGISTRO"
            principio_activo = str(form.get(f"principio_activo_{idx}", "") or "").strip() or None

            await _upsert_detail_product(
                detail=detail,
                lote=lote,
                fecha_vencimiento=fecha_vencimiento,
                costo_caja=costo_caja,
                unidades_por_caja=unidades_por_caja,
                precio_venta_unidad=precio_venta_unidad,
                marca_laboratorio=marca_laboratorio,
                registro_invima=registro_invima,
                principio_activo=principio_activo,
            )

    order.estado = PurchaseStatus.CONFIRMED
    session.add(order)
    await session.commit()

    return HTMLResponse(
        '<div class="bg-emerald-100 border-l-4 border-emerald-500 text-emerald-900 p-6 rounded-lg shadow">'
        '<h3 class="font-black text-xl mb-2">Inventario Abastecido Exitosamente</h3>'
        '<p>Se normalizó el inventario con lote, vencimiento e identificación INVIMA por línea.</p>'
        '<button onclick="window.location.reload()" class="mt-4 bg-white text-emerald-700 px-4 py-2 rounded border border-emerald-200">Cargar otra factura</button>'
        '</div>'
    )
