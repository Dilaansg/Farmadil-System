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
- Estado: pendiente.
- Accion: crear productos nuevos automaticamente o bloquear confirmacion con error de negocio explicito.
- Criterio de aceptacion: ningun item de factura se pierde en confirmacion.

2. Reducir riesgo XSS en rutas HTMX/HTMLResponse.
- Estado: pendiente.
- Accion: migrar render dinamico a Jinja2 con autoescape o escape estricto.
- Criterio de aceptacion: inputs/strings de usuario no se renderizan sin sanitizar.

3. Captura de excepciones tipadas.
- Estado: pendiente.
- Accion: reemplazar except Exception en rutas criticas por errores concretos.
- Criterio de aceptacion: errores con trazabilidad y respuesta consistente.

## Fase 3 - Calidad y automatizacion (21-45 dias)

1. Pipeline CI obligatorio.
- Estado: pendiente.
- Accion: ruff + pytest + smoke startup.
- Criterio de aceptacion: merge bloqueado si falla quality gate.

2. Pruebas de regresion de negocio.
- Estado: pendiente.
- Accion: tests para compras (preview/confirm), productos (campos extendidos), POS (checkout).
- Criterio de aceptacion: cobertura de flujos criticos y no solo auth.

3. Migraciones Alembic reales para schema.
- Estado: pendiente.
- Accion: mover ALTER runtime a migraciones versionadas.
- Criterio de aceptacion: startup no altera estructura en caliente.

## Fase 4 - Evolucion funcional (45-90 dias)

1. Lotes y vencimientos.
- Estado: pendiente.
- Impacto: control sanitario y rotacion FEFO.

2. Reposicion inteligente.
- Estado: pendiente.
- Impacto: menor quiebre de stock y mejor planeacion de compras.

3. Dashboard KPI operativo.
- Estado: pendiente.
- Impacto: visibilidad de margenes, rotacion y alertas.

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
