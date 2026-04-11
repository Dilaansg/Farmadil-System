"""
app/core/database.py
────────────────────
Configuración del motor de base de datos async y fábrica de sesiones.

Exporta:
    engine          → AsyncEngine (SQLAlchemy)
    AsyncSessionLocal → async_sessionmaker
    create_db_tables()  → Crea tablas (solo para dev/testing)
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Motor async de PostgreSQL ─────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,           # Muestra SQL en consola en modo debug
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,                # Detecta conexiones caídas automáticamente
)

# ── Fábrica de sesiones async ─────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,            # Evita lazy-loading errors post-commit
    autocommit=False,
    autoflush=False,
)


async def create_db_tables() -> None:
    """
    Crea todas las tablas definidas con SQLModel.
    ⚠️  Solo usar en testing o desarrollo inicial.
    En producción, usar Alembic (alembic upgrade head).
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("Tablas de base de datos creadas/verificadas.")


async def drop_db_tables() -> None:
    """
    Elimina todas las tablas.
    ⚠️  SOLO para entornos de testing. NUNCA en producción.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    logger.warning("Todas las tablas de base de datos fueron eliminadas.")
