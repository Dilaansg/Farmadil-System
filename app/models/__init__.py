"""app/models/__init__.py — Re-exporta todos los modelos para que Alembic los detecte."""
from app.models.user import User  # noqa: F401

__all__ = ["User"]
