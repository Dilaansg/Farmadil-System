# 🕷️ Estrategia de Scraping — Farmadil System

> **Propósito:** Este documento define exactamente qué se va a obtener mediante scraping web de sitios farmacéuticos colombianos, con qué objetivo dentro del sistema, y qué sitios serán las fuentes de datos.
>
> El scraping **no es para copiar precios de venta al público** del competidor, sino para construir una **base de conocimiento farmacéutica** que haga al sistema más inteligente y autónomo.

---

## 🎯 Sitios Objetivo

| Sitio | URL | Por qué |
|---|---|---|
| **Farmadil** | farmadil.com.co | Fuente primaria — coincide con la marca |
| **La Rebaja** | larebajaonline.com | Mayor catálogo farmacéutico en Colombia |
| **Cruz Verde** | cruzverde.com.co | Referencia de precios y nombres comerciales |
| **Locatel** | locatelcolombia.com | Medicamentos + parafarmacia (cremas, cosméticos) |
| **Drogas La Economía** | drogaslaeconomia.com | Farmacias populares |
| **SISPRO / INVIMA** | gov.co / invima.gov.co | Registro oficial de medicamentos — base legal |

---

## 📦 Qué se va a Scrapear

### 1. 🗂️ Base de Datos de Medicamentos (Catálogo Maestro)

**Objetivo:** Poblar la tabla `products` con un catálogo de referencia de medicamentos comerciales antes de que el usuario ingrese facturas.

**Qué se extrae:**
- ✅ Nombre comercial del producto (ej: "Dolex Forte 500mg x 100 tab")
- ✅ Nombre genérico / principio activo (ej: "Acetaminofén")
- ✅ Presentación / forma farmacéutica (tabletas, cápsulas, sobres, jarabe, crema...)
- ✅ Concentración (ej: 500mg, 10mg/5ml)
- ✅ Número de unidades por empaque (ej: x10, x50, x100)
- ✅ Código de barras (si está visible)
- ✅ Laboratorio / marca fabricante
- ✅ Categoría farmacológica (analgésico, antihistamínico, antihipertensivo...)

**Uso en Farmadil:**
- Prellenar el formulario "Ingresar Producto" al buscar por nombre
- Alimentar el motor de detección IA de medicamentos (`medication_rules.py`)
- Autocompletar `unidades_por_caja` en la ingesta de facturas

---

### 2. 🖼️ Imágenes de Productos

**Objetivo:** Reemplazar los placeholder generados dinámicamente por imágenes reales de cada medicamento para el catálogo visual.

**Qué se extrae:**
- ✅ Foto de la caja / empaque del producto (imagen principal del producto en el e-commerce)
- ✅ URL de imagen en alta resolución o calidad media mínima (>200px)

**Reglas de calidad:**
- Solo imágenes que muestren el empaque real del producto (no genéricas)
- Almacenadas en `app/static/products/` con nombre normalizado (ej: `acetaminofen_500mg.jpg`)
- Si hay varias fotos, guardar la foto de frente de la caja

**Uso en Farmadil:**
- Mostrar en el catálogo visual ("Ver Inventario")
- Mostrar en el POS al buscar productos
- Mostrar en el formulario de edición al seleccionar un producto

---

### 3. 💰 Precios de Referencia (Inteligencia Competitiva)

> [!NOTE]
> Los precios NO se usan para copiar directamente al competidor — se usan como **referencia de mercado** para validar que el margen configurado sea competitivo.

**Qué se extrae:**
- ✅ Precio público de venta (PVP) del producto en cada farmacia
- ✅ Precio de oferta / descuento vigente (si aplica)
- 🔄 Actualización periódica sugerida: semanal o quincenal

**Uso en Farmadil:**
- En la tabla de ingesta de facturas: mostrar badge "Precio mercado: $X,XXX" como referencia
- Alerta si el precio de venta configurado es muy superior o inferior al promedio del mercado
- Futuro: panel de "Inteligencia competitiva" con comparativa por medicamento

---

### 4. 🏷️ Registro INVIMA (Validación Legal)

**Fuente:** [INVIMA Open Data](https://www.datos.gov.co/Salud-y-Protecci-n-Social/INVIMA-Registros-Sanitorias-Vigentes/dwr3-gw2i) — dataset público del gobierno colombiano.

**Qué se extrae / importa:**
- ✅ Número de registro sanitario oficial (RS INVIMA)
- ✅ Nombre del producto registrado
- ✅ Titular del registro (laboratorio)
- ✅ Fecha de vencimiento del registro
- ✅ Estado: Vigente / Vencido / Cancelado

**Uso en Farmadil:**
- Badge de validez legal en la tarjeta del catálogo (🟢 INVIMA Vigente / 🔴 Vencido)
- Al ingresar un producto por factura: advertencia si no tiene registro o está vencido
- Búsqueda inteligente: al tipear "loratadina 10mg", autocompletar desde el registro INVIMA

> [!IMPORTANT]
> El dataset INVIMA es público y se actualiza regularmente en el portal de datos abiertos del gobierno. **No requiere scraping** — se puede descargar como CSV/API directamente.

---

## 🏗️ Arquitectura Técnica Propuesta

```
scraping/
├── spiders/
│   ├── larebaja_spider.py       # Scraper La Rebaja (Scrapy/Playwright)
│   ├── cruzverde_spider.py      # Scraper Cruz Verde
│   └── locatel_spider.py        # Scraper Locatel
├── pipelines/
│   ├── image_downloader.py      # Descarga y normaliza imágenes
│   ├── product_normalizer.py    # Limpia nombres, quita tildes, normaliza mg/ml
│   └── db_importer.py           # Inserta en farmadil.db via SQLModel
├── invima/
│   └── import_invima_csv.py     # Importador del CSV oficial del INVIMA
└── scheduler.py                 # Actualización periódica (Weekly cron)
```

**Librerías recomendadas:**
- `Scrapy` + `scrapy-playwright` (para sitios con JS/React)
- `httpx` + `BeautifulSoup` (para scraping ligero de páginas simples)
- `Pillow` (procesamiento y resize de imágenes)
- `pandas` (normalización de datos del CSV INVIMA)

---

## 📋 Prioridad de Implementación

| # | Tarea | Impacto | Esfuerzo |
|---|---|---|---|
| 1 | Importar CSV INVIMA | 🔴 Alto | 🟢 Bajo |
| 2 | Scrapear catálogo La Rebaja | 🔴 Alto | 🟡 Medio |
| 3 | Descargar imágenes | 🟡 Medio | 🟢 Bajo |
| 4 | Precios de referencia | 🟡 Medio | 🟡 Medio |
| 5 | Scheduler automático | 🟢 Bajo | 🔴 Alto |

---

> [!TIP]
> Comienza con el import del CSV de INVIMA — es gratuito, legal, no requiere scraping y da inmediatamente una base de ~15,000 medicamentos con nombre, laboratorio y estado de registro.
