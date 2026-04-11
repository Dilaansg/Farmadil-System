"""
app/tests/conftest.py
──────────────────────
Fixtures compartidos para todos los tests.
Configura una base de datos en memoria (o de testing) y un cliente HTTP async.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.dependencies.db import get_db
from main import app

# ── Motor de BD para testing (SQLite en memoria) ──────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Crea las tablas antes de los tests y las elimina al final."""
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Provee una sesión de BD de testing limpia por cada test."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()  # Revertir cambios tras cada test


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """
    Cliente HTTP async con la BD de testing inyectada.
    Reemplaza la dependencia get_db con la sesión de testing.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()
