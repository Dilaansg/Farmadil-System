# FastAPI SaaS Boilerplate

> **Stack:** FastAPI · SQLModel · PostgreSQL · Redis · Alembic · uv · Docker

Boilerplate de producción para proyectos SaaS con Python. Levantable en < 5 minutos.

---

## 🏗️ Arquitectura

```
F0/
├── main.py                      # Entry point FastAPI (lifespan, CORS, routers)
├── pyproject.toml               # Dependencias y config (uv)
├── docker-compose.yml           # PostgreSQL + Redis locales
├── alembic.ini                  # Config de migraciones
├── alembic/
│   ├── env.py                   # Entorno async de migraciones
│   └── versions/                # Archivos de migración generados
└── app/
    ├── api/
    │   └── v1/
    │       ├── __init__.py      # Router v1 agregado
    │       └── routes/
    │           ├── auth.py      # POST /auth/register, /auth/login, /auth/refresh
    │           └── users.py     # GET/PATCH/DELETE /users/me, GET /users/
    ├── core/
    │   ├── config.py            # Settings (Pydantic BaseSettings) + .env
    │   ├── database.py          # AsyncEngine + AsyncSessionLocal
    │   ├── security.py          # bcrypt hash + JWT create/decode
    │   └── logging.py           # Logger JSON (prod) / Pretty (dev)
    ├── models/
    │   ├── base.py              # AuditableBase (timestamps, soft-delete)
    │   └── user.py              # SQLModel → tabla `users`
    ├── schemas/
    │   ├── user.py              # UserCreate, UserLogin, UserResponse
    │   └── token.py             # Token
    ├── repositories/
    │   └── user_repository.py   # CRUD DB + Soft Delete Filters
    ├── services/
    │   ├── auth_service.py      # Lógica: register, login, refresh
    │   └── user_service.py      # Lógica: update, deactivate, list
    ├── dependencies/
    │   ├── db.py                # SessionDep (get_db)
    │   └── auth.py              # CurrentUser, CurrentAdmin
    ├── middleware/
    │   └── error_handler.py     # Manejadores globales de errores
    ├── utils/
    │   └── helpers.py           # UUID, UTC, tokens, paginación
    └── tests/
        ├── conftest.py          # Fixtures: BD in-memory, cliente HTTP
        ├── unit/
        │   └── test_security.py
        └── integration/
            └── test_auth.py
```

---

## ⚡ Setup en 5 Minutos

### 1. Instalar dependencias

```bash
# Instalar uv (gestor de paquetes)
pip install uv

# Crear entorno virtual e instalar dependencias
uv venv
uv sync
```

### 2. Configurar variables de entorno

```bash
# Copiar el template y editar con tus valores
cp .env.example .env
```

Editar `.env` — mínimo obligatorio:
- `POSTGRES_PASSWORD` — password de PostgreSQL
- `JWT_SECRET_KEY` — generar con: `openssl rand -hex 32`

### 3. Levantar la infraestructura (PostgreSQL + Redis)

```bash
docker compose up -d
```

Verificar que estén corriendo:
```bash
docker compose ps
```

### 4. Crear las tablas con Alembic

```bash
# Instalar psycopg2 para las migraciones (sync)
uv add psycopg2-binary --dev

# Generar migración inicial
alembic revision --autogenerate -m "init: tabla users"

# Aplicar migración
alembic upgrade head
```

### 5. Correr el servidor

```bash
uvicorn main:app --reload
```

Abrir en el navegador:
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

---

## 🧪 Tests

```bash
# Instalar dependencias de dev (incluye pytest, httpx, etc.)
uv sync --all-extras

# Correr todos los tests
pytest

# Con cobertura
pytest --cov=app --cov-report=html
```

> Los tests de integración usan **SQLite en memoria** — no necesitan Docker corriendo.

---

## 📌 Endpoints Disponibles

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/health` | — | Health check |
| `POST` | `/api/v1/auth/register` | — | Registrar usuario |
| `POST` | `/api/v1/auth/login` | — | Login (form) → JWT |
| `POST` | `/api/v1/auth/refresh` | Bearer refresh | Renovar tokens |
| `GET` | `/api/v1/users/me` | Bearer access | Ver perfil propio |
| `PATCH` | `/api/v1/users/me` | Bearer access | Actualizar perfil |
| `DELETE` | `/api/v1/users/me` | Bearer access | Desactivar cuenta |
| `GET` | `/api/v1/users/` | Bearer (admin) | Listar usuarios |

---

## 🔧 Comandos Útiles

```bash
# Generar nueva migración después de modificar modelos
alembic revision --autogenerate -m "descripcion del cambio"

# Aplicar todas las migraciones pendientes
alembic upgrade head

# Ver historial de migraciones
alembic history

# Revertir última migración
alembic downgrade -1

# Formatear y lintear código
ruff check . --fix
ruff format .
```

---

## 🚀 Variables de Entorno (referencia)

| Variable | Descripción | Default |
|----------|-------------|---------|
| `APP_ENV` | `development` / `production` | `development` |
| `POSTGRES_*` | Credenciales PostgreSQL | Ver `.env.example` |
| `REDIS_*` | Config Redis | Ver `.env.example` |
| `JWT_SECRET_KEY` | Secreto para firmar JWT | **Sin default seguro** |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Vida del access token | `30` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Vida del refresh token | `7` |
| `ALLOWED_ORIGINS` | CORS origins (separados por coma) | `localhost:3000,5173` |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` | `INFO` |

---

> **Nota sobre producción:** En `APP_ENV=production`, los endpoints `/docs`, `/redoc` y `/openapi.json` se deshabilitan automáticamente, y el logging cambia a formato JSON.
