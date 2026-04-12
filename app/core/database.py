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

# ── Motor async de PostgreSQL / SQLite ────────────────────────────────
connect_args = {}
if settings.database_url_async.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# Evitar argumentos de pooling (pool_size, etc) si es SQLite
engine_kwargs = {
    "echo": settings.app_debug,
    "pool_pre_ping": True,
}
if not settings.database_url_async.startswith("sqlite"):
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_async_engine(
    settings.database_url_async,
    connect_args=connect_args,
    **engine_kwargs
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
    await _migrate_product_columns()


async def _migrate_product_columns() -> None:
    """
    Migración segura: agrega columnas nuevas a `products` si no existen.
    SQLite no tiene IF NOT EXISTS para ALTER TABLE, así que se hace
    introspectando las columnas existentes primero.
    """
    NEW_COLUMNS = [
        ("registro_invima",  "TEXT"),
        ("principio_activo", "TEXT"),
        ("estado_invima",    "TEXT"),
        ("laboratorio",      "TEXT"),
    ]
    async with engine.begin() as conn:
        # Obtener columnas existentes
        result = await conn.execute(
            __import__("sqlalchemy").text("PRAGMA table_info(products)")
        )
        existing = {row[1] for row in result.fetchall()}

        for col_name, col_type in NEW_COLUMNS:
            if col_name not in existing:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        f"ALTER TABLE products ADD COLUMN {col_name} {col_type}"
                    )
                )
                logger.info("Columna agregada a products: %s", col_name)


async def drop_db_tables() -> None:
    """
    Elimina todas las tablas.
    ⚠️  SOLO para entornos de testing. NUNCA en producción.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    logger.warning("Todas las tablas de base de datos fueron eliminadas.")
