"""
run.py
──────
Script de arranque para desarrollo y producción.
Lee host/port directamente del .env vía Settings.

Uso:
    python run.py
"""
import uvicorn

from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
