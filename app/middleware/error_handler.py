"""
app/middleware/error_handler.py
────────────────────────────────
Manejadores globales de errores para FastAPI.

Captura excepciones no manejadas y las convierte en respuestas
JSON consistentes, en lugar de exponer traceback al cliente.

Registro en main.py:
    from app.middleware.error_handler import register_exception_handlers
    register_exception_handlers(app)
"""
import traceback

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos los manejadores de errores globales en la app FastAPI."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Formatea HTTPExceptions con estructura JSON consistente."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "status_code": exc.status_code,
                "detail": exc.detail,
            },
            headers=exc.headers or {},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Formatea errores de validación de Pydantic con mensajes legibles.
        Retorna 422 con detalle de los campos que fallaron.
        """
        errors = []
        for error in exc.errors():
            field = " → ".join(str(loc) for loc in error.get("loc", []))
            errors.append({"field": field, "message": error["msg"]})

        logger.warning(
            "Error de validación en %s %s",
            request.method,
            request.url.path,
            extra={"errors": errors},
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "status_code": 422,
                "detail": "Error de validación en los datos enviados.",
                "errors": errors,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """
        Captura ValueErrors lanzados desde services y los convierte en 400.
        Convención: los services usan ValueError para errores de negocio esperados.
        """
        logger.info("Error de negocio: %s", str(exc))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": True,
                "status_code": 400,
                "detail": str(exc),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Последний recurso: captura cualquier excepción no manejada.
        Loguea el traceback completo pero NO lo expone al cliente.
        """
        logger.error(
            "Excepción no manejada en %s %s: %s",
            request.method,
            request.url.path,
            str(exc),
            extra={"traceback": traceback.format_exc()},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "status_code": 500,
                "detail": "Error interno del servidor. Por favor intenta más tarde.",
            },
        )
