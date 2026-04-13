# 🏥 Farmadil System - Estado Actual del Sistema

Este documento describe la arquitectura, stack tecnológico y funcionalidades actuales del sistema **Farmadil System**.

## 🛠️ Stack Tecnológico
El proyecto está construido bajo una arquitectura moderna híbrida (Backend API + Server-Side Rendering con interactividad dinámica), utilizando las siguientes tecnologías:

- **Backend / Core**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3) con ASGI (`uvicorn`). Seleccionado por su alto rendimiento, asincronismo nativo y validación de datos automática con Pydantic.
- **Base de Datos**: **SQLite** (archivo `farmadil.db`) mediante la librería asíncrona `aiosqlite` para entornos de desarrollo.
- **ORM**: [SQLModel](https://sqlmodel.tiangolo.com/) + SQLAlchemy asíncrono. Facilita la creación de modelos de base de datos compatibles directamente con la validación de Pydantic.
- **Frontend Interactivo**: Implementado directamente en las vistas HTML usando [HTMX](https://htmx.org/) (para evitar recargas de página y consumir la API dinámicamente) y [Tailwind CSS](https://tailwindcss.com/) (vía CDN) para un diseño visual moderno, minimalista y responsivo.
- **Seguridad**: Autenticación mediante **JWT (JSON Web Tokens)** y encriptación de contraseñas con bcrypt.

## ⚙️ Arquitectura de Carpetas y Módulos
El proyecto sigue un patrón modular limpio estructurado por capas:
- `app/api/v1/`: Define los endpoints (FastAPI routers).
- `app/core/`: Configuraciones de inicio, variables de entorno, seguridad y base de datos (engine).
- `app/models/`: Representación de las tablas de la BD (SQLModel). Todas heredan de `AuditableBase` para Soft Delete y auditoría temporal.
- `app/schemas/`: Modelos Pydantic para la entrada y salida de datos de la API.
- `app/services/`: Lógica de negocio (Business Layer). Aquí se hacen las reglas y validaciones complejas.
- `app/repositories/`: Capa de interacción directa con la base de datos (CRUD). Separa la base de datos de la lógica.
- `app/templates/`: Vistas de interfaz de usuario en formato HTML usando el motor Jinja2.

## 🚀 Funcionalidades Activas

### 1. 🔐 Seguridad y Gestión de Usuarios (RBAC)
- Autenticación y control de acceso (Login por validación de credenciales a cambio de token JWT).
- Roles de usuario configurables (ej. SUPERADMIN, ADMIN, CAJERO).
- Todos los modelos (Tablas) incluyen Soft-delete automático (`is_deleted`) para no borrar datos contables o históricos por accidente.

### 4. 🧠 Abastecimiento Inteligente (Ingesta de Facturas)
- **Parser Multi-formato**: Soporte para ingesta de facturas en Excel (.xlsx) y Facturación Electrónica XML (UBL 2.1).
- **IA de Reconocimiento**: Algoritmo que detecta automáticamente si un producto es medicamento (basado en nombres, concentraciones y formas farmacéuticas) o artículo de consumo general.
- **Detección Automática de Empaques**: Motor Regex que extrae unidades por caja directamente del nombre (ej: "Tapabocas x 50") y deshabilita o habilita la venta por unidad/sobre según corresponda.
- **Motor de Precios Dinámico**: 
    - Sincronización en tiempo real de 3 vías: **Margen % ↔️ Precio Caja ↔️ Precio Unidad**.
    - Redondeo inteligente a denominaciones legales colombianas (COP).
    - Alertas visuales de rentabilidad negativa (detección de pérdida en rojo).

### 5. 🎨 Interfaz de Usuario "Modern-SSR"
El sistema cuenta con un frontend integrado en la ruta `/`:
- **Búsqueda Dinámica**: Al escribir en la búsqueda del catálogo principal `(inventory_search.html)`, la página consulta a la base de datos y utilizando HTMX renderiza las tarjetas HTML del medicamento instantáneamente.
- **Dashboard de Abastecimiento**: Vista especializada para arrastrar facturas, visualizar el impacto en el inventario antes de confirmar y ajustar estrategias de precios de forma masiva.
- **Edición Rápida en Vivo**: Los productos se pueden actualizar directamente desde las tarjetas de búsqueda o la tabla de pre-visualización de facturas.

## 🎯 Arranque Rápido ("Quick Start")
Toda la gestión del sistema y variables de entorno está concentrada en el archivo `.env`.

Para iniciar en modo desarrollo y autorecarga (hot-reload):
```powershell
python run.py
```
El servidor quedará expuesto por convención en `http://localhost:8000`. 
La documentación técnica del Backend se autogenera en `http://localhost:8000/docs`.

## 🧰 Convenciones de Mantenimiento
- Si una modificación introduce nuevas librerías de terceros, actualizar `requirements.txt` y sincronizar el entorno virtual activo.
- Si el cambio es importante y afecta arquitectura, flujos, módulos principales o comportamiento visible, actualizar este documento para mantener la descripción del sistema al día.

## ✅ Actualización Técnica (2026-04-12)
- Se estabilizó el flujo de autenticación: `POST /api/v1/auth/login` acepta `email` y `username` (form-data).
- El contrato de token de login ahora devuelve `access_token`, `refresh_token` y `token_type`.
- Se reforzó la validación de contraseña (mínimo 8, máximo 72, con mayúscula, minúscula y número).
- Se fijó compatibilidad de hashing en entorno actual con `bcrypt==4.0.1`.
- Se alineó `ProductService` para persistir campos extendidos del producto (INVIMA, laboratorio, unidades por caja, etc.).
