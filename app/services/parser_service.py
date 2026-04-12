import io
from lxml import etree
import pandas as pd
import re
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel

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
        try:
            tree = etree.parse(io.BytesIO(file_bytes))
            root = tree.getroot()
        except etree.XMLSyntaxError:
            raise ValueError("El archivo subido no es un XML válido.")

        # Namespaces comunes en UBL (Factura Electrónica)
        namespaces = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        }
        
        try:
            # Obtener datos generales de la factura
            numero_factura = root.xpath('.//cbc:ID/text()', namespaces=namespaces)[0]
            
            proveedor_party = root.find('.//cac:AccountingSupplierParty/cac:Party', namespaces=namespaces)
            proveedor_nombre = proveedor_party.xpath('.//cac:PartyName/cbc:Name/text()', namespaces=namespaces)[0]
            proveedor_nit = proveedor_party.xpath('.//cac:PartyIdentification/cbc:ID/text()', namespaces=namespaces)[0]

            # Iterar sobre las líneas de detalle de la factura (InvoiceLine)
            detalles = []
            invoice_lines = root.findall('.//cac:InvoiceLine', namespaces=namespaces)
            
            for line in invoice_lines:
                cantidad = line.xpath('.//cbc:InvoicedQuantity/text()', namespaces=namespaces)[0]
                costo = line.xpath('.//cac:Price/cbc:PriceAmount/text()', namespaces=namespaces)[0]
                nombre = line.xpath('.//cac:Item/cbc:Description/text()', namespaces=namespaces)[0]

                detalles.append(ParsedInvoiceDetail(
                    nombre_producto=str(nombre).strip(),
                    cantidad=int(float(cantidad)),
                    costo_unitario=Decimal(str(costo))
                ))
            
            return ParsedInvoice(
                proveedor_nombre=proveedor_nombre,
                proveedor_nit=proveedor_nit,
                numero_factura=numero_factura,
                detalles=detalles
            )
        except IndexError:
            raise ValueError("El XML no cumple con el estándar esperado (UBL), faltan nodos requeridos (ID, PartyName, InvoiceLine, etc).")

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
