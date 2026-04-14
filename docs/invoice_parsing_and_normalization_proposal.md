# Error de parsing e incapacidad de sugerir INVIMA

**Resumen rápido**

Al parsear la factura `storage/invoices/ad09017638790002600000145.xml` el servicio devuelve líneas con datos incompletos: no sugiere registros INVIMA, no extrae principio activo ni mapea laboratorios de forma fiable. El XML original está embebido dentro de un `AttachedDocument` y contiene un `Invoice` en CDATA, y el parser previo fallaba por XPaths indexados que lanzaban IndexError o no eran tolerantes a variaciones de namespace/prefijos.

**Evidencia**

- Archivo reproducible: `storage/invoices/ad09017638790002600000145.xml`
- Parser afectado: `app/services/parser_service.py` (método `parse_ubl_xml`)
- Resultados observados en UI/preview: todos los productos muestran "INVIMA sugerido: Sin sugerencia", "Principio activo: N/D" y lotes/vencimientos vacíos o con placeholder.

**Síntomas concretos**

- IndexError o fallback que termina en "Sin sugerencia" porque el código indexaba la primera coincidencia XPath sin comprobaciones.
- Tokens de nombre (dosis, envase, marca) no normalizados → baja tasa de matching.
- Búsqueda FTS y fallback LIKE insuficientes (posible FTS mal configurado o queries demasiado restrictivas).
- Heurística de extracción de marca/especificaciones frágil (solo separadores `-` o `*`).
- No se extraen `LotIdentification` ni `ManufactureDate/ExpiryDate` desde nodos alternativos (ej. `AdditionalItemProperty`, `LotIdentification`).

**Causas raíz (principales)**

1. Normalización pobre: no se separan dosis, pack sizes, formas farmacéuticas ni marcas; no se remueven caracteres ruidosos ni se expanden abreviaturas.
2. Índice de catálogo insuficiente: falta columna `nombre_normalizado` y/o FTS5 mal configurado (unicode61, remove_diacritics), lo que degrada recall.
3. Matching monolítico: solo FTS o LIKE, sin re-ranking fuzzy/token-aware; por tanto matches semánticos o parciales fallan.
4. Extracción XML incompleta: no se buscan rutas alternativas (local-name, AdditionalItemProperty) para lote/vencimiento.
5. Falta de un loop de corrección humana que recoja pares (texto_factura → id_catalogo) para mejorar la cobertura.

**Propuesta de solución (resumida, pipeline)**

1. Normalizer robusto (`app/utils/normalizer.py`)
   - De-accent, lowercase, collapse whitespace, strip punctuation salvo signos relevantes.
   - Extraer atributos: `concentracion`, `forma_farmaceutica`, `unidades_por_caja`, `presentacion`, `marca_candidate`.
   - Remover tokens de dosis/pack cuando se genera `nombre_base` y `nombre_normalizado`.
   - Expandir abreviaturas y aplicar stopwords.

2. Indexado y DB
   - Añadir `nombre_normalizado` y `nombre_tokens` en `reference_products`.
   - Backfill normalizando registros existentes.
   - Crear FTS5 virtual table con `tokenize='unicode61 remove_diacritics=2'` o almacenar `nombre_normalizado` en FTS.
   - Añadir `lab_aliases` para canonicalizar laboratorios.

3. Matching híbrido (`app/services/matching_service.py`)
   - Candidate retrieval: FTS5 -> top N.
   - Re-ranking: RapidFuzz token_set/partial ratios + token overlap + brand/principio-activo boosts.
   - Scores combinados (pesos α/β/γ ajustables) y umbrales para auto-aceptar (Recall@1 alto) o mostrar top-3 para revisión.

4. Mejor extracción XML
   - Extraer `LotIdentification`, `ManufactureDate`, `ExpiryDate` de `InvoiceLine` y `AdditionalItemProperty` usando XPaths namespaced y `local-name()` fallback.
   - Mapear manufacturer/brand desde `cac:BrandName`, `cac:AdditionalProperty` o sufijos en `cbc:Description`.

5. Feedback / UI
   - Previsualización muestra top-3 coincidencias con puntuación y botón para seleccionar/corregir.
   - Almacenar correcciones para alimentar reglas/lexicon y dataset de entrenamiento.

6. Métricas y validación
   - Construir conjunto de validación (200–1000 líneas) con ground-truth.
   - Medir Recall@1, Recall@5, MRR; usar para ajustar pesos.

**Tareas priorizadas (rápido → impacto)**

- Paso 1 (0.5–1 día): Implementar `app/utils/normalizer.py` y tests básicos.
- Paso 2 (0.5–1 día): Añadir `nombre_normalizado` columna y backfill script; crear/ajustar FTS5.
- Paso 3 (1–2 días): Implementar `matching_service` con RapidFuzz re-ranking y conectar `ParserService.match_with_invima` al nuevo flujo.
- Paso 4 (1 día): Mejor extracción de lote/vencimiento en `ParserService.parse_ubl_xml` y mapear brand.
- Paso 5 (1–2 días): UI de previsualización top-3 + persistir correcciones.
- Paso 6 (1–2 días): Construir dataset, ejecutar benchmarks y ajustar pesos.

**Impacto esperado**

- Aumento importante en matches automáticos (Recall@1) y reducción de revisiones manuales.
- Mejora en extracción de principio activo y laboratorio por separación correcta de marca/dosis.
- Datos de lote/vencimiento correctamente poblados en la previsualización.

**Riesgos y notas**

- Si el catálogo `reference_products` está incompleto, hay un límite práctico; la solución mejora recall pero no crea datos que no existan.
- FTS5 en SQLite requiere configuración/privilegios correctos; en entornos con otro motor (Postgres) hay que adaptar (pg_trgm, GIN).
- Opcional: embeddings/ML semántico si el presupuesto/tiempo lo permiten; útil para long-tail.

---

**Siguiente paso sugerido**

Implemento el Paso 1: crear `app/utils/normalizer.py` con funciones `normalize_text`, `extract_attributes`, y pruebas unitarias en `tests/unit/test_normalizer.py`. ¿Confirmas que proceda? Si confirmas, empiezo y luego ejecuto los tests locales.
