from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.routes.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Todo lo que ocupe startup (ej. creación de tablas en dev si no usas alembic aún)
    yield
    # Todo lo que ocupe shutdown
    pass


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
    lifespan=lifespan,
)

# Configuración de CORS dinámico desde .env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Integración de Controladores (Routers)
app.include_router(auth_router, prefix="/api/v1")

@app.get("/health", tags=["Salud"])
async def health_check():
    """Para que los Load Balancers comprueben que la API está viva."""
    return {"status": "ok", "environment": settings.app_env}
