"""
app/utils/import_invima.py
==========================
Script de importacion COMPLETA del CSV oficial del INVIMA (159k registros).
No agrupa en base de datos, permite mantener historial legal completo.

Uso:
    python -m app.utils.import_invima
"""
# -*- coding: utf-8 -*-
import argparse
import sqlite3
import unicodedata
import re
import sys
from pathlib import Path

import pandas as pd

# -- Configuracion -----------------------------------------------------------
DEFAULT_CSV   = Path("data/invima_master.csv")
CATALOG_DB    = Path("catalog_reference.db")
CHUNK_SIZE    = 10_000

# -- Helpers -----------------------------------------------------------------

def normalize_text(text: str) -> str:
    """Minusculas, sin tildes, sin dobles espacios."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def create_tables(conn: sqlite3.Connection) -> None:
    """Crea la tabla principal y la virtual FTS5 para busqueda."""
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS reference_products")
    cursor.execute("""
        CREATE TABLE reference_products (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            registro_invima   TEXT,
            nombre_comercial  TEXT NOT NULL,
            nombre_normalizado TEXT,
            principio_activo  TEXT,
            titular           TEXT,
            descripcion       TEXT,     -- Descripcion comercial (empaque)
            forma_farmaceutica TEXT,
            concentracion     TEXT,
            atc               TEXT,
            descripcion_atc   TEXT,
            estado_registro   TEXT,
            estado_cum        TEXT,
            fecha_vencimiento TEXT,
            expediente_cum    TEXT,
            consecutivo_cum   TEXT
        )
    """)

    cursor.execute("DROP TABLE IF EXISTS reference_fts")
    cursor.execute("""
        CREATE VIRTUAL TABLE reference_fts USING fts5(
            nombre_comercial,
            principio_activo,
            titular,
            content='reference_products',
            content_rowid='id',
            tokenize='unicode61'
        )
    """)

    conn.commit()
    sys.stdout.write("[OK] Tablas base de datos de referencia creadas.\n")
    sys.stdout.flush()


def import_chunks(csv_path: Path, conn: sqlite3.Connection) -> int:
    """Lee el CSV en chunks y lo inserta en reference_products (Sin Agrupar)."""
    cursor = conn.cursor()
    total_inserted = 0
    chunk_num = 0

    # Detectar encoding
    encoding = "utf-8"
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            pd.read_csv(csv_path, nrows=1, encoding=enc)
            encoding = enc
            break
        except Exception:
            continue

    sys.stdout.write(f"[INFO] Importando CSV (159k registros) con encoding={encoding} ...\n")
    sys.stdout.flush()

    reader = pd.read_csv(
        csv_path,
        chunksize=CHUNK_SIZE,
        encoding=encoding,
        on_bad_lines="skip",
        low_memory=False,
    )

    for chunk in reader:
        chunk_num += 1
        chunk.columns = [c.strip().lower() for c in chunk.columns]

        # Validacion de columnas requeridas
        if 'producto' not in chunk.columns:
            sys.stderr.write(f"[ERROR] Columna 'producto' no encontrada en chunk {chunk_num}\n")
            continue

        rows = []
        for _, row in chunk.iterrows():
            nombre = str(row.get("producto", "") or "").strip()
            if not nombre:
                continue
            
            rows.append((
                str(row.get("registrosanitario", "") or "").strip(),
                nombre,
                normalize_text(nombre),
                str(row.get("principioactivo", "") or "").strip(),
                str(row.get("titular", "") or "").strip(),
                str(row.get("descripcioncomercial", "") or "").strip(),
                str(row.get("formafarmaceutica", "") or "").strip(),
                str(row.get("concentracion", "") or "").strip(),
                str(row.get("atc", "") or "").strip(),
                str(row.get("descripcionatc", "") or "").strip(),
                str(row.get("estadoregistro", "") or "").strip(),
                str(row.get("estadocum", "") or "").strip(),
                str(row.get("fechavencimiento", "") or "").strip(),
                str(row.get("expedientecum", "") or "").strip(),
                str(row.get("consecutivocum", "") or "").strip()
            ))

        if rows:
            cursor.executemany("""
                INSERT INTO reference_products
                    (registro_invima, nombre_comercial, nombre_normalizado,
                     principio_activo, titular, descripcion,
                     forma_farmaceutica, concentracion, atc, 
                     descripcion_atc, estado_registro, estado_cum, 
                     fecha_vencimiento, expediente_cum, consecutivo_cum)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, rows)
            total_inserted += len(rows)

        conn.commit()
        sys.stdout.write(f"\r  Chunk {chunk_num:>3} -- Procesando: {total_inserted:,} registros   ")
        sys.stdout.flush()

    sys.stdout.write("\n")
    return total_inserted


def build_fts_index(conn: sqlite3.Connection) -> None:
    """Llena la tabla FTS5 desde reference_products."""
    sys.stdout.write("[INFO] Construyendo indice de busqueda FTS5 (Puede tardar 1-2 min) ...\n")
    sys.stdout.flush()
    conn.execute("INSERT INTO reference_fts(reference_fts) VALUES('rebuild')")
    conn.commit()
    sys.stdout.write("[OK] Indice de busqueda FTS5 optimizado.\n")
    sys.stdout.flush()


# -- Punto de entrada --------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Importador INVIMA Completo (159k)")
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="Ruta al CSV")
    parser.add_argument("--db",  default=str(CATALOG_DB),  help="Ruta a la DB destino")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    db_path  = Path(args.db)

    if not csv_path.exists():
        sys.stderr.write(f"[ERROR] No se encuentra el archivo {csv_path}\n")
        sys.exit(1)

    # Conectar y configurar SQLite para performance masiva
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=20000")
    conn.execute("PRAGMA temp_store=MEMORY")

    create_tables(conn)
    total = import_chunks(csv_path, conn)
    build_fts_index(conn)

    # Indices adicionales para agrupacion rapida en UI
    sys.stdout.write("[INFO] Creando indices de rendimiento ...\n")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_group ON reference_products(nombre_normalizado, titular, concentracion)")
    conn.commit()
    conn.close()

    sys.stdout.write(f"\n[DONE] Importacion exitosa: {total:,} registros en {db_path}\n")
    sys.stdout.write("       Base de datos lista para consultas agrupadas.\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
