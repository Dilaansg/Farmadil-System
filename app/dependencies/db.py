"""
app/dependencies/db.py
───────────────────────
Dependencia de inyección de sesión de base de datos para FastAPI.

Uso en un router:
    @router.get("/")
    async def my_endpoint(session: SessionDep):
        ...
"""
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Generador async que provee una sesión de BD por request.
    La sesión se cierra automáticamente al finalizar el request.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# Tipo conveniente para inyección en routers (evita repetir Annotated[...])
SessionDep = Annotated[AsyncSession, Depends(get_db)]
