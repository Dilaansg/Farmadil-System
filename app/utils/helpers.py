"""
app/utils/helpers.py
─────────────────────
Utilidades genéricas reutilizables en todo el proyecto.
Agregar aquí funciones que no pertenecen a ningún dominio específico.
"""
import hashlib
import secrets
import string
import uuid
from datetime import UTC, datetime


def generate_uuid() -> uuid.UUID:
    """Genera un UUID v4 aleatorio."""
    return uuid.uuid4()


def utcnow() -> datetime:
    """Retorna el timestamp actual en UTC (timezone-aware)."""
    return datetime.now(UTC)


def generate_random_token(length: int = 32) -> str:
    """
    Genera un token único aleatorio criptográficamente seguro.
    Útil para tokens de confirmación de email, reset de password, etc.
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def hash_string(value: str, algorithm: str = "sha256") -> str:
    """
    Genera un hash de un string (no bcrypt — usar para IDs o checksums).
    Para passwords, usar hash_password() de app.core.security.
    """
    return hashlib.new(algorithm, value.encode()).hexdigest()


def paginate(total: int, page: int, page_size: int) -> dict:
    """
    Calcula metadatos de paginación.

    Returns:
        dict con keys: total, page, page_size, total_pages, has_next, has_prev
    """
    total_pages = max(1, -(-total // page_size))  # ceil division
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }
