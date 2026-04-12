"""
app/api/v1/routes/catalog.py
──────────────────────────────
Endpoints HTMX para búsqueda en el catálogo INVIMA (catalog_reference.db).
Flujo:
  1. /search?q=...      → tarjetas agrupadas + botón "crear manualmente"
  2. /presentations?id=  → lista de variantes legales de un grupo
  3. La selección final invoca selectProduct() en JS que carga el formulario.
"""
import html as html_module
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse

from app.core.catalog_database import search_catalog, catalog_db_exists, CATALOG_DB_PATH

router = APIRouter(prefix="/catalog", tags=["Catalog Reference"])


def _esc(text: str) -> str:
    """Escapa HTML para prevenir XSS en contenido dinámico."""
    return html_module.escape(str(text)) if text else ""


# ─────────────────────────────────────────────────────────────────────────────
# 1. BÚSQUEDA AGRUPADA
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/search", response_class=HTMLResponse)
async def catalog_search_htmx(q: str = Query(default="", min_length=0)) -> HTMLResponse:
    """Retorna tarjetas agrupadas por clase de producto + botón 'crear manual'."""
    if not catalog_db_exists():
        return HTMLResponse(
            '<div class="p-6 text-center text-amber-600 text-sm font-medium">'
            '⚠️ Catálogo INVIMA no disponible. Ejecuta: <code>python -m app.utils.import_invima</code></div>'
        )

    if len(q.strip()) < 2:
        return HTMLResponse("")

    results = await search_catalog(q, limit=40)

    # Construir tarjetas
    rows_html = ""
    for r in results:
        nombre = _esc(r.get("nombre_comercial", ""))
        titular = _esc(r.get("titular", ""))
        principio = _esc(r.get("principio_activo", ""))
        concentracion = _esc(r.get("concentracion", ""))
        forma = _esc(r.get("forma_farmaceutica", ""))
        num = r.get("num_presentaciones", 1)
        rid = r.get("id", 0)

        subtitle_parts = [p for p in [principio, concentracion, forma] if p]
        subtitle = " · ".join(subtitle_parts)

        rows_html += f"""
        <button type="button"
                hx-get="/api/v1/catalog/presentations?id={rid}"
                hx-target="#catalog-results"
                hx-swap="innerHTML"
                class="w-full text-left flex items-start gap-3 px-5 py-4 hover:bg-blue-50/80
                       transition-all border-b border-gray-100 last:border-0 group">
            <div class="flex-1 min-w-0">
                <div class="text-blue-700 font-black text-[10px] uppercase tracking-wider mb-0.5
                            flex items-center gap-2 truncate">
                    {titular or "Sin laboratorio"}
                    <span class="bg-blue-50 text-blue-500 border border-blue-100
                                 px-1.5 py-px rounded text-[9px] shrink-0">{num} var.</span>
                </div>
                <div class="font-bold text-gray-900 text-sm leading-snug
                            group-hover:text-blue-700 transition-colors">{nombre}</div>
                <div class="text-[11px] text-gray-400 mt-0.5 truncate">{subtitle}</div>
            </div>
            <div class="self-center opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor"
                     viewBox="0 0 24 24"><path d="M9 5l7 7-7 7" stroke-width="2"
                     stroke-linecap="round" stroke-linejoin="round"/></svg>
            </div>
        </button>
        """

    # Sin resultados
    if not results:
        rows_html = f"""
        <div class="px-5 py-6 text-center text-gray-400 text-sm">
            Sin resultados para "<span class="font-semibold text-gray-500">{_esc(q)}</span>"
        </div>
        """

    # Botón "Crear manualmente" — SIEMPRE al final
    manual_btn = f"""
    <button type="button"
            hx-get="/api/v1/products/htmx/new-form?nombre={_esc(q)}"
            hx-target="#main-container"
            hx-swap="innerHTML"
            class="w-full text-left flex items-center gap-3 px-5 py-4
                   bg-gray-50 hover:bg-emerald-50 transition-all group border-t border-gray-200">
        <div class="w-8 h-8 rounded-full bg-emerald-100 text-emerald-600
                    flex items-center justify-center shrink-0 group-hover:bg-emerald-200 transition-colors">
            <svg class="w-4 h-4" fill="none" stroke="currentColor"
                 viewBox="0 0 24 24"><path d="M12 4v16m8-8H4" stroke-width="2.5"
                 stroke-linecap="round"/></svg>
        </div>
        <div>
            <div class="font-bold text-gray-700 text-sm group-hover:text-emerald-700 transition-colors">
                Crear producto manualmente
            </div>
            <div class="text-[11px] text-gray-400">No está en el catálogo INVIMA</div>
        </div>
    </button>
    """

    return HTMLResponse(f"""
    <div class="divide-y divide-gray-50">
        {rows_html}
        {manual_btn}
    </div>
    """)


# ─────────────────────────────────────────────────────────────────────────────
# 2. PRESENTACIONES (DRILL-DOWN)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/presentations", response_class=HTMLResponse)
async def catalog_presentations(id: int) -> HTMLResponse:
    """Retorna las variantes legales (CUM/Registro) de un grupo."""
    from app.core.catalog_database import get_presentations_by_id

    presentations = await get_presentations_by_id(id)

    if not presentations:
        return HTMLResponse(
            '<div class="p-6 text-center text-gray-400 text-sm">No se encontraron variantes</div>'
        )

    header = presentations[0]

    items_html = ""
    for p in presentations:
        desc = _esc(p.get("descripcion", "")) or "Sin descripción comercial"
        reg = _esc(p.get("registro_invima", ""))
        titular = _esc(p.get("titular", ""))
        nombre = _esc(p.get("nombre_comercial", ""))
        principio = _esc(p.get("principio_activo", ""))
        categoria = _esc(p.get("descripcion_atc", ""))
        est = p.get("estado_cum", "")

        status_cls = (
            "bg-emerald-50 text-emerald-600 border-emerald-200"
            if est == "Activo"
            else "bg-gray-50 text-gray-400 border-gray-200"
        )

        # JSON seguro para el onclick (evitar comillas rotas)
        import json
        data_json = json.dumps({
            "nombre": p.get("nombre_comercial", ""),
            "principio_activo": p.get("principio_activo", ""),
            "registro_invima": p.get("registro_invima", ""),
            "laboratorio": p.get("titular", ""),
            "descripcion_comercial": p.get("descripcion", ""),
            "categoria": p.get("descripcion_atc", ""),
        }, ensure_ascii=True)

        items_html += f"""
        <button type="button"
                onclick='selectProduct({data_json})'
                class="w-full text-left p-4 hover:bg-blue-50 transition-colors
                       border-b border-gray-50 last:border-0 flex items-center
                       justify-between group">
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                    <span class="text-[9px] font-bold {status_cls} border
                                 px-2 py-0.5 rounded-full">{_esc(est) or "—"}</span>
                    <span class="text-[9px] font-mono text-gray-400
                                 tracking-tight truncate">{reg}</span>
                </div>
                <div class="text-xs font-semibold text-gray-600
                            group-hover:text-blue-700 transition-colors truncate">{titular}</div>
                <div class="text-[11px] text-gray-400 mt-0.5 line-clamp-2">{desc}</div>
            </div>
            <svg class="w-4 h-4 text-gray-200 group-hover:text-blue-500 transition-colors shrink-0 ml-2"
                 fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M12 4v16m8-8H4" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
        """

    header_name = _esc(header.get("nombre_comercial", ""))

    return HTMLResponse(f"""
    <div class="flex flex-col max-h-[420px]">
        <!-- Header sticky -->
        <div class="bg-gray-50 px-5 py-3 border-b border-gray-200
                    flex items-center justify-between sticky top-0 z-10 shrink-0">
            <div class="min-w-0">
                <div class="text-[10px] font-black text-gray-400 uppercase tracking-widest">
                    Seleccionar Variante
                </div>
                <h3 class="font-bold text-gray-900 text-sm truncate">{header_name}</h3>
            </div>
            <button onclick="document.getElementById('catalog-results').innerHTML=''"
                    class="p-1.5 hover:bg-gray-200 rounded-full transition-colors
                           text-gray-400 shrink-0" title="Cerrar">
                <svg class="w-5 h-5" fill="none" stroke="currentColor"
                     viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12"
                     stroke-width="2" stroke-linecap="round"/></svg>
            </button>
        </div>
        <!-- Lista scrollable -->
        <div class="overflow-y-auto divide-y divide-gray-50">
            {items_html}
        </div>
    </div>
    """)


# ─────────────────────────────────────────────────────────────────────────────
# 3. UTILIDADES
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/search-json")
async def catalog_search_json(q: str = Query(default="", min_length=2)) -> JSONResponse:
    """Búsqueda JSON para uso programático."""
    results = await search_catalog(q, limit=20)
    return JSONResponse(content={"results": results, "count": len(results)})


@router.get("/status")
async def catalog_status() -> JSONResponse:
    """Verifica si el catálogo de referencia está disponible."""
    db_path = CATALOG_DB_PATH
    exists = db_path.exists()
    size_mb = round(db_path.stat().st_size / 1_048_576, 1) if exists else 0
    return JSONResponse(content={
        "available": exists,
        "size_mb": size_mb,
        "path": str(db_path.resolve()),
    })
