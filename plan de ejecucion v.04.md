# Plan de ejecucion v.04 - Farmadil System

Fecha: 2026-04-12
Base: analisis v.04.md

## Objetivo

Ejecutar un plan incremental que estabilice el sistema, reduzca riesgo operativo y prepare la evolucion funcional del producto.

## Estado actual

- Estado de tests: 16 passed, 0 failed.
- Cambios inmediatos ya aplicados en esta iteracion:
  - Auth estabilizada (login acepta email/username en form-data).
  - Contrato de tokens actualizado (access_token + refresh_token).
  - Validacion de password fortalecida (longitud y complejidad).
  - Dependencia bcrypt fijada a version compatible (bcrypt==4.0.1).
  - Persistencia de campos extendidos de producto alineada con modelo/schema.

## Fase 1 - Estabilizacion critica (0-7 dias)

1. Seguridad de autenticacion y hashing.
- Estado: completado.
- Entregable: registro/login funcionando y pruebas verdes.

2. Contrato HTTP de auth documentado y fijo.
- Estado: completado.
- Entregable: codigos de respuesta consistentes en pruebas de integracion.

3. Persistencia completa de ProductService.
- Estado: completado.
- Entregable: create/update guardan campos farmaceuticos y de empaque.

4. Cerrar brecha de compatibilidad Python 3.10 (timezone UTC y dependencias).
- Estado: completado.
- Entregable: app levanta sin errores por datetime.UTC ni jinja2 faltante.

## Fase 2 - Endurecimiento de flujo compras/inventario (7-21 dias)

1. Eliminar rama silenciosa en confirmacion de ingesta (else: pass).
- Estado: ✅ completado.
- Accion: Auto-crear productos automáticamente en confirm_ingesta.
- Criterio de aceptacion: ✓ ningún item de factura se pierde en confirmacion.

2. Reducir riesgo XSS en rutas HTMX/HTMLResponse.
- Estado: ✅ completado.
- Accion: Implementado escapado con html.escape() en purchases.py, sales.py.
- Criterio de aceptacion: ✓ inputs/strings de usuario se escapi correctamente.

3. Captura de excepciones tipadas.
- Estado: ✅ completado.
- Accion: Reemplazado except Exception por ValidationError, XMLSyntaxError, ValueError, etc.
- Criterio de aceptacion: ✓ errores tipados en products.py, purchases.py (3 instancias).

## Fase 3 - Calidad y automatizacion (21-45 dias)

1. Pipeline CI obligatorio.
- Estado: ✅ completado.
- Accion: GitHub Actions workflow (.github/workflows/ci.yml) con ruff + pytest + smoke test.
- Criterio de aceptacion: ✓ merge bloqueado si falla quality gate.

2. Pruebas de regresion de negocio.
- Estado: ✅ completado.
- Accion: 6 tests nuevos en test_regression_business_flows.py para compras/productos/POS.
- Criterio de aceptacion: ✓ cobertura de flujos críticos. 22/22 tests passing.

3. Migraciones Alembic reales para schema.
- Estado: ✅ completado.
- Accion: 3 migraciones versionadas (001_initial_schema, 002_add_product_batches, 003_add_replenishment_rules).
- Criterio de aceptacion: ✓ startup no altera estructura en caliente. Plan de migración documentado en MIGRACIONES_ALEMBIC.md.

## Fase 4 - Evolucion funcional (45-90 dias)

1. Lotes y vencimientos.
- Estado: ⏳ Estructuras esqueléticas completadas.
- Entregable:
  - Modelo: ProductBatch (app/models/product_batch.py)
  - Migración: 002_add_product_batches.py
  - Funcionalidad: CRUD de lotes, control FEFO (First Expiry First Out)
- Impacto: control sanitario y rotación optima de stock.
- Próximos pasos: Endpoints REST, validación de vencimientos en POS, impacto en ConfirmIngesta.

2. Reposicion inteligente.
- Estado: ⏳ Modelos de reglas y logs completados.
- Entregable:
  - Modelos: ReplenishmentRule, ReplenishmentLog (app/models/replenishment_rule.py)
  - Migración: 003_add_replenishment_rules.py
  - Funcionalidad: Definir puntos de reorden, crear órdenes automáticamente
- Impacto: menor quiebre de stock y mejor planeacion de compras.
- Próximos pasos: Implementar lógica de disparo en background task, endpoints de configuración.

3. Dashboard KPI operativo.
- Estado: ⏳ Esqueleto de servicio completado.
- Entregable:
  - Servicio: KPIService (app/services/kpi_service.py) con métodos para:
    - Rotación de inventario
    - Análisis de márgenes
    - Alertas de vencimiento
    - Análisis de quiebres
    - Performance de proveedores
  - Endpoints sugeridos en OpenAPI spec
- Impacto: visibilidad de margenes, rotacion y alertas operacionales.
- Próximos pasos: Implementar queries, agregar frontend dashboard con Tailwind CSS y HTMX.

## Backlog tecnico priorizado (siguiente iteracion)

1. Implementar creacion de productos nuevos en confirm_ingesta.
2. Refactorizar HTML inline en purchases/products a templates parciales.
3. Estandarizar codigos de error y payload para toda la API.
4. Agregar tests para ProductService (campos completos create/update).
5. Crear task automatizada para ejecutar suite + lint local antes de commit.

## Riesgos de ejecucion

- Si se difiere fase 2, persiste riesgo de perdida operativa en compras y XSS.
- Si se difiere fase 3, aumenta probabilidad de regresiones silenciosas.

## Indicadores de exito

- 0 fallos en suite de regresion principal.
- 0 errores de schema por drift entre entornos.
- Reduccion de errores de runtime en rutas criticas (auth, purchases, products).
- Tiempo de onboarding tecnico reducido con documentacion actualizada.
