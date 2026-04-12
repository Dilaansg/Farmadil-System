"""
app/core/catalog_database.py
─────────────────────────────
Motor de solo-lectura para catalog_reference.db (datos INVIMA).
Estrategia de búsqueda:
  1. FTS5 con corrección de ambigüedad (table aliases explícitos).
  2. Fallback LIKE multi-columna (nombre, principio, titular, registro).
  3. Agrupamiento por clase de producto para UI limpia.
  4. Drill-down por ID para ver presentaciones legales.
"""
import unicodedata
import re
from pathlib import Path
from typing import Optional

import aiosqlite

CATALOG_DB_PATH = Path("catalog_reference.db")


def _normalize(text: str) -> str:
    """Minúsculas, sin tildes, sin dobles espacios."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def catalog_db_exists() -> bool:
    return CATALOG_DB_PATH.exists() and CATALOG_DB_PATH.stat().st_size > 0


async def search_catalog(query: str, limit: int = 40) -> list[dict]:
    """
    Búsqueda unificada en catalog_reference.db.
    Busca en TODAS las columnas relevantes: nombre, principio activo,
    titular (laboratorio) y registro INVIMA.
    Retorna resultados AGRUPADOS por clase de producto.
    """
    if not catalog_db_exists():
        return []
    q = query.strip()
    if len(q) < 2:
        return []

    norm_q = _normalize(q)
    results = []

    async with aiosqlite.connect(CATALOG_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # ── Estrategia 1: FTS5 (rápido, busca en nombre + principio + titular) ──
        try:
            # Tokenizar la query para FTS5: cada palabra con prefix match
            tokens = norm_q.split()
            fts_query = " ".join(f"{t}*" for t in tokens)

            sql_fts = """
                SELECT
                    rp.id,
                    rp.nombre_comercial,
                    rp.nombre_normalizado,
                    rp.principio_activo,
                    rp.titular,
                    rp.forma_farmaceutica,
                    rp.concentracion,
                    rp.registro_invima,
                    rp.descripcion_atc,
                    COUNT(*) as num_presentaciones
                FROM reference_fts fts
                JOIN reference_products rp ON rp.id = fts.rowid
                WHERE fts.reference_fts MATCH ?
                GROUP BY rp.nombre_normalizado, rp.concentracion
                ORDER BY
                    (rp.nombre_normalizado LIKE ?) DESC,
                    rank
                LIMIT ?
            """
            async with db.execute(sql_fts, (fts_query, f"{norm_q}%", limit)) as cursor:
                rows = await cursor.fetchall()
                results = [dict(r) for r in rows]
        except Exception:
            pass  # Fallback below

        # ── Estrategia 2: LIKE multi-columna (fallback + registro INVIMA) ──
        if not results:
            like_pattern = f"%{norm_q}%"
            sql_like = """
                SELECT
                    rp.id,
                    rp.nombre_comercial,
                    rp.nombre_normalizado,
                    rp.principio_activo,
                    rp.titular,
                    rp.forma_farmaceutica,
                    rp.concentracion,
                    rp.registro_invima,
                    rp.descripcion_atc,
                    COUNT(*) as num_presentaciones
                FROM reference_products rp
                WHERE
                    rp.nombre_normalizado LIKE ?
                    OR LOWER(rp.principio_activo) LIKE ?
                    OR LOWER(rp.titular) LIKE ?
                    OR LOWER(rp.registro_invima) LIKE ?
                GROUP BY rp.nombre_normalizado, rp.concentracion
                ORDER BY
                    (rp.nombre_normalizado LIKE ?) DESC,
                    rp.nombre_comercial
                LIMIT ?
            """
            async with db.execute(
                sql_like,
                (like_pattern, like_pattern, like_pattern, like_pattern, f"{norm_q}%", limit),
            ) as cursor:
                rows = await cursor.fetchall()
                results = [dict(r) for r in rows]

    return results


async def get_presentations_by_id(product_id: int) -> list[dict]:
    """
    Dado el ID de un 'representante' de grupo, retorna TODAS las
    presentaciones legales (CUM/Registro INVIMA) de su misma clase.
    """
    if not catalog_db_exists():
        return []

    async with aiosqlite.connect(CATALOG_DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # 1. Obtener la 'clase' del representante
        async with db.execute(
            "SELECT nombre_normalizado, concentracion FROM reference_products WHERE id = ?",
            (product_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return []

        # 2. Buscar todas las variantes de esa clase con limpieza de duplicados agresiva
        # Usamos una subconsulta con ORDER BY p_orden para que GROUP BY elija el registro 'Activo' si existe.
        sql_variants = """
            SELECT * FROM (
                SELECT *, 
                       CASE estado_cum WHEN 'Activo' THEN 1 ELSE 2 END as p_orden,
                       -- Clave de empaque simplificada (sin puntos, espacios extra, ni guiones) para agrupar
                       UPPER(REPLACE(REPLACE(REPLACE(descripcion, '.', ''), ' ', ''), '-', '')) as key_desc
                FROM reference_products
                WHERE nombre_normalizado = ? AND concentracion = ?
                ORDER BY p_orden ASC
            )
            GROUP BY registro_invima, titular, key_desc
            ORDER BY p_orden ASC, titular, descripcion
        """
        async with db.execute(sql_variants, (row["nombre_normalizado"], row["concentracion"])) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_catalog_by_id(product_id: int) -> Optional[dict]:
    """Busca un producto exacto por su ID interno en el catálogo."""
    if not catalog_db_exists():
        return None
    async with aiosqlite.connect(CATALOG_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM reference_products WHERE id = ?", (product_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
