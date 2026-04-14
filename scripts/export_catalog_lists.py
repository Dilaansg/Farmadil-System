"""
Script: export_catalog_lists.py

Ejecuta dos consultas sobre `catalog_reference.db` y escribe los resultados
en `scripts/catalog_lists.py` como variables Python:

- LABS: lista de dicts con claves: lab_key, representante, regs, productos_count
- NAME_ROLES: diccionario nombre_normalizado -> {num_presentaciones, titulares_unificados_list}

Uso:
    python scripts/export_catalog_lists.py

Salida:
    scripts/catalog_lists.py
"""
from pathlib import Path
import sqlite3
import pprint
import unicodedata
import re

DB_PATH = Path("catalog_reference.db")
OUT_PATH = Path(__file__).parent / "catalog_lists.py"

QUERY_LABS = """
-- Construimos primero la clave simplificada en una subconsulta para evitar problemas
SELECT
  lab_key,
  MIN(titular) AS representante,
  COUNT(DISTINCT registro_invima) AS regs,
  COUNT(*) AS productos_count
FROM (
  SELECT
    titular,
    registro_invima,
    UPPER(TRIM(
      REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
        titular, '.', ''), ',', ''), '-', ''), '/', ''), '  ', ' '), ' LTDA', ''), ' S A S', ''), ' S A', ''), ' SA', '')
    )) AS lab_key
  FROM reference_products
  WHERE titular IS NOT NULL AND TRIM(titular) <> ''
) AS sub
GROUP BY lab_key
ORDER BY productos_count DESC;
"""

QUERY_NAME_ROLES = """
SELECT
  nombre_normalizado,
  COUNT(*) AS num_presentaciones,
  GROUP_CONCAT(DISTINCT TRIM(titular)) AS titulares_unificados
FROM reference_products
WHERE nombre_normalizado IS NOT NULL AND TRIM(nombre_normalizado) <> ''
GROUP BY nombre_normalizado
ORDER BY num_presentaciones DESC
LIMIT 500;
"""


def fetch_rows(query: str):
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB no encontrada en {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.execute(query)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def build_name_roles_map(rows):
    out = {}
    for r in rows:
        name = r.get('nombre_normalizado')
        # split titulares_unificados into list
        t = r.get('titulares_unificados') or ''
        # SQLite returns GROUP_CONCAT with comma-separated values by default
        titulares = [x.strip() for x in t.split(',')] if t else []
        titulares = [x for x in titulares if x]
        out[name] = {
            'num_presentaciones': r.get('num_presentaciones'),
            'titulares': titulares,
        }
    return out


def normalize_lab_name(name: str) -> str:
    if not name:
        return ""
    # de-accent, lower, remove punctuation and common legal suffixes
    name = unicodedata.normalize("NFKD", str(name))
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower()
    # remove punctuation
    name = re.sub(r"[\.,\-/()\']", " ", name)
    # remove common corporate suffixes
    name = re.sub(r"\b(ltda|ltda\.|sas|s\.a\.s\.|s a s|s a|sa|s\.a\.)\b", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def write_output(labs, name_roles):
    content_lines = []
    content_lines.append('# Auto-generated catalog lists')
    content_lines.append('from typing import List, Dict')
    content_lines.append('')
    content_lines.append('LABS = ' + pprint.pformat(labs, width=120))
    content_lines.append('')
    content_lines.append('NAME_ROLES = ' + pprint.pformat(name_roles, width=120))
    content_lines.append('')
    # Build simple LAB_NAMES list from LABS representatives
    lab_names = [r.get('representante') for r in labs if r.get('representante')]
    # Normalize lab names into simple identifiers
    normalized = [normalize_lab_name(n) for n in lab_names]
    # dedupe and sort
    unique_sorted = sorted(set([n for n in normalized if n]))
    content_lines.append('LAB_NAMES = ' + pprint.pformat(unique_sorted, width=120))
    content = '\n'.join(content_lines) + '\n'
    OUT_PATH.write_text(content, encoding='utf-8')


def main():
    print('Ejecutando consultas...')
    labs = fetch_rows(QUERY_LABS)
    names = fetch_rows(QUERY_NAME_ROLES)
    name_roles = build_name_roles_map(names)
    print(f'Resultados: labs={len(labs)}, name_roles={len(name_roles)}')
    print(f'Escribiendo {OUT_PATH} ...')
    write_output(labs, name_roles)
    print('Listas exportadas correctamente.')


if __name__ == '__main__':
    main()
