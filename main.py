"""
main.py
────────
Punto de entrada de la aplicación FastAPI.

Para correr en desarrollo:
    uvicorn main:app --reload

Para correr en producción (reemplazar workers según CPU count):
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_v1_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.middleware.error_handler import register_exception_handlers

# Configurar logging lo antes posible
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Gestiona el ciclo de vida de la aplicación.
    El código antes del `yield` corre al arrancar.
    El código después del `yield` corre al apagar.
    """
    logger.info(
        "🚀 Iniciando %s en modo %s",
        settings.app_name,
        settings.app_env.upper(),
    )
    # ── Startup ─────────────────────────────────────────────────────
    # Nota: las migraciones se corren con `alembic upgrade head`, no aquí.
    # Si quieres crear tablas automáticamente en dev, descomenta:
    # from app.core.database import create_db_tables
    # await create_db_tables()

    yield

    # ── Shutdown ─────────────────────────────────────────────────────
    logger.info("🛑 Apagando %s...", settings.app_name)
    from app.core.database import engine
    await engine.dispose()


# ── Instancia principal de FastAPI ────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description="API SaaS — Boilerplate con FastAPI + SQLModel + PostgreSQL + Redis",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Middlewares ───────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Manejadores de errores globales ───────────────────────────────────
register_exception_handlers(app)

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(api_v1_router)


# ── Health Check ──────────────────────────────────────────────────────
@app.get("/health", tags=["System"], summary="Health check")
async def health_check() -> dict:
    """Endpoint de salud para load balancers y monitoreo."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "version": "1.0.0",
    }
