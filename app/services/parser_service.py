import io
import re
import unicodedata
from datetime import date
from decimal import Decimal
from typing import List, Optional

import aiosqlite
from lxml import etree
import pandas as pd
from pydantic import BaseModel

from app.core.catalog_database import CATALOG_DB_PATH

# ── Modelos de Datos del Parser ──────────────────────────────────────
class ParsedInvoiceDetail(BaseModel):
    nombre_producto: str
    cantidad: int
    costo_unitario: Decimal          # costo por caja/unidad factura
    unidades_por_caja: int = 1       # cuántas tabletas/pastillas trae la caja
    sugerencia_nuevo_precio: Optional[Decimal] = None   # precio venta por caja
    sugerencia_precio_unidad: Optional[Decimal] = None  # precio venta por pastilla
    costo_anterior: Optional[Decimal] = None
    subio_costo: bool = False
    es_medicamento: bool = False
    lote: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    registro_invima_sugerido: Optional[str] = None
    principio_activo_sugerido: Optional[str] = None
    marca_laboratorio_sugerida: Optional[str] = None

class ParsedInvoice(BaseModel):
    proveedor_nombre: str
    proveedor_nit: str
    numero_factura: str
    detalles: List[ParsedInvoiceDetail]

class ParserService:
    """
    Servicio de Ingesta Inteligente de Facturas.
    Soporta parsing de Excel (.xlsx) y Archivos Electrónicos XML (UBL 2.1).
    """

    @staticmethod
    def _normalize(text: str) -> str:
        text = unicodedata.normalize("NFKD", str(text))
        text = "".join(c for c in text if not unicodedata.combining(c))
        text = re.sub(r"\s+", " ", text).strip().lower()
        return text

    @staticmethod
    def extract_brand_from_invoice_text(name: str) -> Optional[str]:
        """Intenta extraer marca/laboratorio cuando viene como sufijo en el texto."""
        if not name:
            return None

        # Ejemplos esperados: "ACETAMINOFEN 500MG - GENFAR", "... * MK"
        parts = re.split(r"\s[-*]\s", name)
        if len(parts) >= 2:
            candidate = parts[-1].strip(" .")
            if 2 <= len(candidate) <= 60:
                return candidate

        return None

    @staticmethod
    def _extract_embedded_invoice_xml(file_bytes: bytes) -> bytes:
        """Soporta AttachedDocument de DIAN extrayendo el XML real en CDATA."""
        raw = file_bytes.decode("utf-8", errors="ignore")
        if "<AttachedDocument" not in raw:
            return file_bytes

        cdata_blocks = re.findall(r"<!\[CDATA\[(.*?)\]\]>", raw, flags=re.DOTALL | re.IGNORECASE)
        for block in cdata_blocks:
            candidate = block.strip()
            if "<Invoice" in candidate or "<CreditNote" in candidate:
                return candidate.encode("utf-8")

        # Fallback: intentar extraer XML embebido sin CDATA estricto
        invoice_match = re.search(r"(<(?:\w+:)?Invoice[\s\S]*</(?:\w+:)?Invoice>)", raw)
        if invoice_match:
            return invoice_match.group(1).encode("utf-8")

        return file_bytes
    @staticmethod
    def is_medication(name: str) -> bool:
        """
        Algoritmo inteligente para detectar si un producto es medicamento o no.
        """
        from app.services.medication_rules import is_medication_by_rule
        
        # 1. Reglas estrictas configurables
        if is_medication_by_rule(name):
            return True

        med_keywords = [
            " jarabe", " tableta", " gragea", " capsula", " cápsula",
            " inyectable", " ampolla", " suspensión", " suspension", " gotas", " gts", " ungüento",
            " unguento", " pomada", " supositorio", " polvo", " solución", " solucion",
            " pastilla", " cap", " tab", " vial", " spray", " inhalador", " sobre"
        ]
        non_med_keywords = [
            "shampoo", "jabon", "jabón", "pañal", "toallita", "algodon", "algodón",
            "cepillo", "crema dental", "seda dental", "desodorante", "bloqueador",
            "protector solar", "condon", "preservativo", "gel", "lubricante",
            "pañito", "biberon", "tetero", "chupo", "gasa", "micropore", "curita", "venda",
            "termometro", "tapabocas", "jeringa", "bisturi", "aguja", "desinfectante", "alcohol"
        ]
        
        name_lower = name.lower()
        
        # 2. Reglas de exclusión explícitas
        for k in non_med_keywords:
            if k in name_lower:
                return False
                
        # 3. Expresión regular para detectar concentraciones (ej. 500 mg, 5 ml, 10 mcg)
        if re.search(r'\b\d+(?:\.\d+)?\s*(mg|ml|mcg|g|ui|u\.i\.|gr)\b', name_lower):
            return True
            
        # 4. Reglas de inclusión por forma farmacéutica genérica
        for k in med_keywords:
            if k in name_lower:
                return True
                
        return False

    @staticmethod
    def parse_xlsx(file_bytes: bytes) -> ParsedInvoice:
        """
        Interpreta un archivo Excel de un proveedor.
        Se asume que tiene columnas reconocibles como 'Nombre', 'Cantidad', 'Costo', etc.
        """
        # Cargar con pandas
        df = pd.read_excel(io.BytesIO(file_bytes))
        
        # Estandarizar nombres de columnas eliminando espacios y pasando a minúsculas
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Mapeo heurístico de columnas basado en palabras clave (Farmacias comunes)
        col_nombre = next((c for c in df.columns if 'nombre' in c or 'descrip' in c or 'producto' in c), None)
        col_cantidad = next((c for c in df.columns if 'cant' in c or 'qty' in c), None)
        col_costo = next((c for c in df.columns if 'costo' in c or 'precio' in c or 'valor' in c), None)
        
        if not col_nombre or not col_cantidad or not col_costo:
            raise ValueError(f"No se pudieron identificar las columnas requeridas (Nombre, Cantidad, Costo) en el Excel. Columnas encontradas: {list(df.columns)}")

        detalles = []
        for _, row in df.iterrows():
            if pd.isna(row[col_nombre]) or pd.isna(row[col_cantidad]) or pd.isna(row[col_costo]):
                continue # Saltar líneas vacías
                
            detalles.append(ParsedInvoiceDetail(
                nombre_producto=str(row[col_nombre]).strip(),
                cantidad=int(row[col_cantidad]),
                costo_unitario=Decimal(str(row[col_costo]))
            ))

        return ParsedInvoice(
            proveedor_nombre="[Proveedor Desconocido - Archivo Excel]",
            proveedor_nit="000000000",
            numero_factura="EXCEL-001",
            detalles=detalles
        )

    @staticmethod
    def parse_ubl_xml(file_bytes: bytes) -> ParsedInvoice:
        """
        Interpreta una Factura Electrónica en formato XML estándar UBL 2.1 
        (Universal Business Language), muy usado en facturación electrónica de LATAM.
        """
        xml_bytes = ParserService._extract_embedded_invoice_xml(file_bytes)

        try:
            tree = etree.parse(io.BytesIO(xml_bytes))
            root = tree.getroot()
        except etree.XMLSyntaxError:
            raise ValueError("El archivo subido no es un XML válido.")

        # Namespaces comunes en UBL (Factura Electrónica)
        namespaces = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        }
        
        # Helper: intentar varias XPaths (namespaced primero, luego local-name fallback)
        def first_text(node, exprs):
            for expr in exprs:
                try:
                    res = node.xpath(expr, namespaces=namespaces)
                except Exception:
                    res = []
                if res:
                    return res[0]
            return None

        # Extraer número de factura
        numero_factura = first_text(root, ['.//cbc:ID/text()', ".//*[local-name()='ID']/text()"])
        if not numero_factura:
            raise ValueError("No se encontró el ID de la factura en el XML (cbc:ID).")

        # Proveedor (nombre y NIT) - intentar rutas namespaced y fallback por local-name
        proveedor_nombre = first_text(root, [
            './/cac:AccountingSupplierParty//cac:PartyName/cbc:Name/text()',
            './/cac:Party//cac:PartyName/cbc:Name/text()',
            ".//*[local-name()='AccountingSupplierParty']//*[local-name()='PartyName']/*[local-name()='Name']/text()",
            ".//*[local-name()='Party']//*[local-name()='PartyName']/*[local-name()='Name']/text()",
        ])
        proveedor_nit = first_text(root, [
            './/cac:AccountingSupplierParty//cac:PartyIdentification/cbc:ID/text()',
            './/cac:Party//cac:PartyIdentification/cbc:ID/text()',
            ".//*[local-name()='AccountingSupplierParty']//*[local-name()='PartyIdentification']/*[local-name()='ID']/text()",
            ".//*[local-name()='Party']//*[local-name()='PartyIdentification']/*[local-name()='ID']/text()",
        ])

        if not proveedor_nombre or not proveedor_nit:
            # Si faltan datos críticos, informar claramente
            raise ValueError("No se encontraron datos del proveedor en el XML (PartyName o PartyIdentification).")

        # Buscar líneas de factura (InvoiceLine)
        invoice_lines = root.findall('.//cac:InvoiceLine', namespaces=namespaces)
        if not invoice_lines:
            invoice_lines = root.findall(".//*[local-name()='InvoiceLine']")

        detalles = []
        for line in invoice_lines:
            cantidad = first_text(line, ['.//cbc:InvoicedQuantity/text()', ".//*[local-name()='InvoicedQuantity']/text()"])
            costo = first_text(line, ['.//cac:Price/cbc:PriceAmount/text()', ".//*[local-name()='Price']/*[local-name()='PriceAmount']/text()", ".//*[local-name()='PriceAmount']/text()"])
            nombre = first_text(line, ['.//cac:Item/cbc:Description/text()', ".//*[local-name()='Item']/*[local-name()='Description']/text()", ".//*[local-name()='Description']/text()"])

            if not cantidad or not costo or not nombre:
                # Saltar líneas incompletas en lugar de fallar todo el parseo
                continue

            detalles.append(ParsedInvoiceDetail(
                nombre_producto=str(nombre).strip(),
                cantidad=int(float(cantidad)),
                costo_unitario=Decimal(str(costo)),
                marca_laboratorio_sugerida=ParserService.extract_brand_from_invoice_text(str(nombre)),
            ))

        if not detalles:
            raise ValueError("El XML no contiene líneas de detalle válidas (InvoiceLine).")

        return ParsedInvoice(
            proveedor_nombre=proveedor_nombre,
            proveedor_nit=proveedor_nit,
            numero_factura=numero_factura,
            detalles=detalles
        )

    @staticmethod
    async def match_with_invima(nombre_factura: str) -> Optional[dict]:
        """
        Busca coincidencias de referencia en catalog_reference.db (FTS o LIKE).
        Retorna sugerencias para registro INVIMA, principio activo y laboratorio.
        """
        if not CATALOG_DB_PATH.exists() or not nombre_factura:
            return None

        norm_name = ParserService._normalize(nombre_factura)
        if len(norm_name) < 2:
            return None

        async with aiosqlite.connect(CATALOG_DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            # 1) Intento FTS5
            try:
                tokens = [t for t in norm_name.split() if len(t) > 1]
                fts_query = " ".join(f"{t}*" for t in tokens[:6])
                if fts_query:
                    sql_fts = """
                        SELECT
                            rp.nombre_comercial,
                            rp.registro_invima,
                            rp.principio_activo,
                            rp.titular
                        FROM reference_fts fts
                        JOIN reference_products rp ON rp.id = fts.rowid
                        WHERE fts.reference_fts MATCH ?
                        ORDER BY rank
                        LIMIT 1
                    """
                    async with db.execute(sql_fts, (fts_query,)) as cur:
                        row = await cur.fetchone()
                        if row:
                            return {
                                "nombre_catalogo": row["nombre_comercial"],
                                "registro_invima": row["registro_invima"],
                                "principio_activo": row["principio_activo"],
                                "marca_laboratorio": row["titular"],
                            }
            except Exception:
                pass

            # 2) Fallback LIKE/ILIKE-style (SQLite uses LIKE + lower)
            like = f"%{norm_name}%"
            sql_like = """
                SELECT
                    nombre_comercial,
                    registro_invima,
                    principio_activo,
                    titular
                FROM reference_products
                WHERE
                    LOWER(nombre_normalizado) LIKE ?
                    OR LOWER(nombre_comercial) LIKE ?
                    OR LOWER(principio_activo) LIKE ?
                ORDER BY LENGTH(nombre_comercial)
                LIMIT 1
            """
            async with db.execute(sql_like, (like, like, like)) as cur:
                row = await cur.fetchone()
                if not row:
                    return None

                return {
                    "nombre_catalogo": row["nombre_comercial"],
                    "registro_invima": row["registro_invima"],
                    "principio_activo": row["principio_activo"],
                    "marca_laboratorio": row["titular"],
                }

    # ── Módulo 2: Redondeo denominaciones Colombia ──────────────────
    @staticmethod
    def round_to_cop(value: Decimal) -> Decimal:
        """
        Redondea un precio al multiple de denominación legal colombiana más cercana.
        Monedas: 50, 100, 200, 500, 1000
        Billetes: 1000, 2000, 5000, 10000, 20000, 50000, 100000
        Regla práctica: se redondea al múltiplo de 100 más próximo para precios menores a $5000,
        y al múltiplo de 500 más próximo para precios mayores a $5000.
        """
        v = int(value)
        if v < 1000:
            # Redondear al múltiplo de 50 más cercano
            return Decimal(round(v / 50) * 50)
        elif v < 5000:
            # Redondear al múltiplo de 100 más cercano
            return Decimal(round(v / 100) * 100)
        elif v < 20000:
            # Redondear al múltiplo de 500 más cercano
            return Decimal(round(v / 500) * 500)
        else:
            # Redondear al múltiplo de 1000 más cercano
            return Decimal(round(v / 1000) * 1000)

    # ── Módulo 3: Sugerencia de Precios ─────────────────────────────
    @staticmethod
    def calculate_price_suggestions(parsed_invoice: ParsedInvoice, db_products: dict, margen_porcentual: float = 0.35) -> ParsedInvoice:
        """
        Toma una factura parseada y un diccionario de productos (Simulando consulta DB).
        Compara el costo_unitario nuevo contra el precio de compra en DB.
        Si sube, sugiere un nuevo precio_venta garantizando el margen de ganancia.
        
        db_products: dict con clave `nombre_producto` o `codigo_barras` map a Product entity.
        margen_porcentual: 0.35 equivale al 35% de margen sobre el precio de venta sugerido.
        """
        for detalle in parsed_invoice.detalles:
            # Detectar si es medicamento inteligentemente
            detalle.es_medicamento = ParserService.is_medication(detalle.nombre_producto)
            
            # Buscar multiplicadores en el nombre (ej. "tapabocas x 50" o "por 20")
            match_unidades = re.search(r'\b(?:x|por)\s*(\d+)\b', detalle.nombre_producto, re.IGNORECASE)
            if match_unidades:
                detalle.unidades_por_caja = int(match_unidades.group(1))
            
            # Calcular precio por unidad (pastilla/tableta o unidades paquete)
            unidades = max(detalle.unidades_por_caja, 1)

            # Buscar si el producto existe actualmente en el inventario
            db_product = next((p for p in db_products.values() if p.nombre.lower() == detalle.nombre_producto.lower()), None)
            
            if db_product:
                detalle.costo_anterior = db_product.precio_compra
                
                if detalle.costo_unitario > db_product.precio_compra:
                    detalle.subio_costo = True
                    precio_caja = detalle.costo_unitario / Decimal(str(1 - margen_porcentual))
                else:
                    detalle.subio_costo = False
                    precio_caja = db_product.precio_venta
            else:
                # Producto nuevo: calcular directamente con margen
                detalle.subio_costo = False
                precio_caja = detalle.costo_unitario / Decimal(str(1 - margen_porcentual))

            # Redondear a denominación colombiana válida
            detalle.sugerencia_nuevo_precio = ParserService.round_to_cop(precio_caja)
            # Precio por unidad individual (tableta/pastilla)
            precio_x_unidad = precio_caja / Decimal(str(unidades))
            detalle.sugerencia_precio_unidad = ParserService.round_to_cop(precio_x_unidad)
                    
        return parsed_invoice
