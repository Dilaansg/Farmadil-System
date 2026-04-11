"""
alembic/env.py
───────────────
Configuración del entorno de Alembic.
Lee la URL de BD del archivo .env a través de config.py.

Soporta dos modos:
    - offline (sin conexión a BD): genera SQL para revisar
    - online (con conexión real): aplica migraciones directamente
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import settings

# ── Importar modelos para que Alembic los detecte en autogenerate ────
import app.models  # noqa: F401
from sqlmodel import SQLModel

# Config object de Alembic
config = context.config

# Sobreescribir la URL de BD con el valor del .env (síncrona para Alembic)
config.set_main_option("sqlalchemy.url", settings.database_url)

# Configurar logging desde alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadatos de los modelos (para autogenerate de migraciones)
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """
    Modo offline: genera SQL sin conectarse a la BD.
    Útil para revisar qué SQL se va a ejecutar antes de aplicarlo.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # Detecta cambios de tipo de columna
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Modo online async: aplica migraciones con conexión real a PostgreSQL."""
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point para el modo online."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
