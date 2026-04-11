"""
app/core/logging.py
───────────────────
Configuración del logger estructurado de la aplicación.

Usa el módulo estándar `logging` con un formateador JSON para producción
y un formateador legible para desarrollo.

Uso:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Servidor iniciado", extra={"port": 8000})
"""
import json
import logging
import sys
from datetime import UTC, datetime

from app.core.config import settings


class _JsonFormatter(logging.Formatter):
    """Formateador que emite cada log como una línea JSON (para producción/monitoreo)."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Añadir contexto extra si existe
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Copiar campos extra del record (agregados via extra={})
        for key, value in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "module", "msecs", "message", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName",
            }:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class _PrettyFormatter(logging.Formatter):
    """Formateador legible con colores ANSI para desarrollo."""

    _COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self._COLORS.get(record.levelname, "")
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"{color}[{timestamp}] {record.levelname:<8}{self._RESET} "
            f"\033[90m{record.name}\033[0m — {record.getMessage()}"
        )


def setup_logging() -> None:
    """
    Configura el sistema de logging de la aplicación.
    Llamar una sola vez al arrancar la app (en main.py o en el lifespan).
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    if settings.is_production:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(_PrettyFormatter())

    # Configurar el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]

    # Silenciar loggers ruidosos de librerías externas
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.app_debug else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger con el nombre del módulo.

    Args:
        name: Normalmente `__name__` del módulo que lo llama.
    """
    return logging.getLogger(name)
