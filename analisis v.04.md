# Analisis v.04 - Farmadil System

Fecha: 2026-04-11

## 1) Resumen ejecutivo

El proyecto tiene una base buena: arquitectura por capas (routes/services/repositories), FastAPI async, SQLModel y una propuesta de UI SSR+HTMX bastante rica para flujos de farmacia (inventario, POS, ingesta de facturas).

Sin embargo, hoy hay deuda tecnica que afecta estabilidad y mantenibilidad:

- La autenticacion esta rota por incompatibilidad de librerias de hashing.
- Hay desalineacion entre modelo/schemas y persistencia de productos.
- Existen flujos de compras que pueden perder informacion de items nuevos.
- Hay riesgo de XSS en endpoints que arman HTML con f-strings y datos no saneados.
- El esquema de BD en SQLite depende de migraciones "en runtime" en lugar de Alembic formal.

Estado actual observado: el servidor levanta, pero los tests muestran fallos funcionales importantes (11 failed, 5 passed).

## 2) Flujo funcional general del sistema

### 2.1 Arranque y ciclo de vida

1. Se inicia via run.py (uvicorn).
2. main.py configura logging, CORS, handlers globales y routers v1.
3. En startup se ejecuta create_db_tables() para crear/verificar tablas.
4. Se aplica una "migracion ligera" en runtime para columnas de products.

### 2.2 Flujo de autenticacion

1. Registro: POST /api/v1/auth/register (crea usuario).
2. Login: POST /api/v1/auth/login con OAuth2PasswordRequestForm.
3. Dependencia get_current_user valida JWT y carga usuario.
4. RoleChecker aplica RBAC para endpoints admin.

### 2.3 Flujo de inventario/productos

1. Crear/editar/listar productos via ProductService/ProductRepository.
2. Rutas HTMX para buscador, formulario y render de cards.
3. Modelo Product incluye campos farmaceuticos (INVIMA, laboratorio, unidades por caja).

### 2.4 Flujo de compras e ingesta

1. Carga de XML/XLSX.
2. Parser identifica items y sugiere precios/margenes.
3. Se guarda orden DRAFT y detalles.
4. Confirmacion suma stock y ajusta precios.

### 2.5 Flujo de ventas (POS)

1. Add-item por codigo de barras.
2. Checkout agrupa items, descuenta stock y registra transaccion+detalles.
3. Operacion transaccional con rollback ante errores de negocio.

## 3) Bugs y errores detectados (priorizados)

## Criticos

1. Incompatibilidad bcrypt/passlib rompe hashing y autenticacion.
- Evidencia: tests unitarios de security fallan con "ValueError: password cannot be longer than 72 bytes..." durante hash_password().
- Causa probable: passlib 1.7.4 + bcrypt 5.0.0 incompatibles.
- Impacto: no funciona registro/login correctamente en varios escenarios.
- Sugerencia: pin de bcrypt compatible con passlib (ej. 4.0.1) o migrar a un stack moderno (pwdlib/argon2) y ajustar tests.

2. ProductService no persiste campos nuevos del schema/modelo.
- Evidencia: ProductCreate y ProductUpdate incluyen unidades_por_caja, registro_invima, principio_activo, estado_invima, laboratorio; pero create_product/update_product no los asignan todos.
- Impacto: datos visibles en UI/ingesta no quedan guardados o quedan incompletos.
- Sugerencia: alinear mapeo completo en create/update y agregar tests de persistencia de todos los campos.

3. Confirmacion de ingesta ignora productos nuevos.
- Evidencia: en purchases confirm, cuando detalle no tiene producto_id cae en else: pass.
- Impacto: items nuevos de factura pueden quedar sin creacion de producto y sin trazabilidad operativa completa.
- Sugerencia: crear producto minimo automaticamente (pendiente de completar) o bloquear confirmacion hasta mapear todos los items.

4. Riesgo de XSS en respuestas HTML construidas con f-strings.
- Evidencia: multiples endpoints retornan HTMLResponse con valores de BD/inputs sin escape consistente (sales, purchases, catalog, products).
- Impacto: posibilidad de inyeccion de scripts si entra contenido malicioso (ej. nombre producto).
- Sugerencia: renderizar siempre por Jinja2 con autoescape o escapar explicitamente todo dato dinamico.

## Altos

5. Drift de esquema: mezcla de create_all + ALTER runtime sin migraciones Alembic formales.
- Evidencia: create_db_tables() + _migrate_product_columns() modifica schema al arrancar.
- Impacto: riesgo de divergencia entre entornos, hardening deficiente en produccion.
- Sugerencia: llevar todos los cambios de schema a Alembic y usar startup sin alteraciones estructurales.

6. Contrato ambiguo en login (OAuth2 form).
- Evidencia: endpoint usa OAuth2PasswordRequestForm (campo username) mientras clientes/tests intentan enviar email.
- Impacto: 422 en clientes no alineados al contrato del endpoint.
- Sugerencia: aceptar explicitamente username/email con normalizacion, documentarlo y homogeneizar tests.

7. Criterios de error no totalmente consistentes (401/403/400/422) en auth.
- Evidencia: pruebas esperan codigos distintos segun caso y actualmente no coinciden.
- Impacto: clientes frontend y tests se rompen por contrato HTTP inestable.
- Sugerencia: definir matriz de errores por caso y aplicarla en rutas/dependencias/handlers.

8. Captura amplia de excepciones en rutas clave.
- Evidencia: except Exception en create/update product y parseo compras.
- Impacto: oculta causas raiz, dificulta observabilidad, convierte errores tecnicos en mensajes poco estructurados.
- Sugerencia: capturar excepciones tipadas (ValidationError, XMLSyntaxError, etc.) y estandarizar respuesta.

## Medios

9. Monolitizacion de rutas UI en strings gigantes.
- Evidencia: products.py y purchases.py concentran mucho HTML + JS inline.
- Impacto: baja mantenibilidad, alta friccion para pruebas y cambios visuales.
- Sugerencia: mover a templates/componentes y separar scripts a static.

10. README y estado real de la plataforma parcialmente desalineados.
- Evidencia: README orientado a PostgreSQL/Redis; entorno actual ejecuta SQLite en dev.
- Impacto: onboarding confuso y setup inconsistentemente reproducible.
- Sugerencia: documentar claramente perfiles dev/local/prod y comandos por perfil.

11. Warnings de Pydantic V2 (class Config legacy).
- Evidencia: warning en schema UserPublic.
- Impacto: deuda tecnica para futuras versiones.
- Sugerencia: migrar a ConfigDict en todos los schemas.

## 4) Oportunidades de optimizacion

1. Performance de catalogo/POS.
- Introducir paginacion real, filtros indexados y busqueda incremental con debounce.
- Evitar render completo de grids en cada request cuando no cambia el dataset.

2. Base de datos.
- Indices compuestos para consultas frecuentes (is_deleted + nombre/codigo).
- Estrategia de migraciones versionadas y seeds controlados por entorno.

3. Dominio de precios.
- Consolidar motor de precios en un servicio unico para no duplicar logica en frontend y backend.
- Registrar historico de cambios de costo/precio para auditoria y analytics.

4. Seguridad.
- Endurecer CSP y sanitizacion de contenido en respuestas HTML dinamicas.
- Rotacion de JWT secret y politicas por entorno.

## 5) Oportunidades de automatizacion

1. CI/CD minima obligatoria.
- Pipeline: ruff + mypy + pytest + smoke startup.
- Bloqueo de merge si falla autentificacion, schema o tests criticos.

2. Pre-commit hooks.
- Formato/lint/type-check antes de commit para bajar errores triviales.

3. Validacion de migraciones.
- Job que valide que modelos y migraciones estan sincronizados.

4. Pruebas de contrato API.
- Contract tests para codigos HTTP y payload de errores por endpoint.

5. Pruebas E2E de flujos HTMX.
- Al menos smoke de: buscar producto, checkout, preview/confirm factura.

6. Observabilidad.
- Logging estructurado uniforme + correlacion de request_id.
- Dashboard basico de errores, tiempos de respuesta y rutas mas usadas.

## 6) Propuestas nuevas para el proyecto

## Propuestas de alto valor (producto)

1. Control por lotes y fechas de vencimiento.
- Trazabilidad por lote, alertas de proximidad de vencimiento y bloqueo de venta vencida.

2. Reposicion inteligente.
- Pronostico simple por rotacion (ventas historicas + estacionalidad basica).
- Sugerencias automaticas de compra por proveedor.

3. Motor de sustitucion terapeutica.
- Sugerir alternativas por principio activo/categoria cuando no hay stock.

4. Integracion contable/fiscal.
- Exportacion de ventas/compras a formato contable y cierre diario automatizado.

5. Multi-sucursal.
- Inventario por sede, transferencias internas y consolidado gerencial.

## Propuestas de experiencia operativa

6. Escaneo masivo y conciliacion de inventario.
- Modo inventario ciclico con pistola y diferencias en tiempo real.

7. Notificaciones operativas.
- Alertas de stock critico, costos anormales o margen negativo por WhatsApp/email.

8. Panel de KPI de farmacia.
- Margen por categoria, top productos, rotacion, quiebres de stock, ticket promedio.

## 7) Roadmap sugerido (30/60/90 dias)

30 dias (estabilizacion):
- Resolver incompatibilidad bcrypt/passlib.
- Alinear auth contract y codigos HTTP.
- Corregir persistencia completa de ProductService.
- Eliminar "pass" en confirmacion de compras.
- Reducir riesgo XSS en rutas mas expuestas.

60 dias (calidad y automatizacion):
- CI con quality gates.
- Migraciones Alembic completas (sin ALTER runtime en startup).
- Cobertura de tests de regresion para auth/inventario/compras.

90 dias (escalado funcional):
- Lotes y vencimientos.
- Dashboard KPI.
- Reposicion inteligente y alertas operativas.

## 8) Riesgos si no se corrige

- Fugas de seguridad (XSS) y errores de autenticacion en produccion.
- Perdida silenciosa de informacion de inventario en ingesta.
- Desalineacion creciente entre codigo, base de datos y documentacion.
- Coste alto de mantenimiento por rutas con logica mezclada UI + negocio.

## 9) Conclusiones

Farmadil tiene una base prometedora y ya cubre procesos core de una farmacia (auth, inventario, POS, compras). El siguiente salto de madurez requiere priorizar estabilizacion tecnica (auth, schema, seguridad HTML, contratos API) y despues fortalecer automatizacion y observabilidad. Con ese orden, el proyecto puede pasar rapidamente de MVP funcional a plataforma operativa robusta.
