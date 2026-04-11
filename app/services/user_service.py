"""
app/services/user_service.py
──────────────────────────────
Lógica de negocio para gestión de usuarios.
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdate


class UserService:
    """Servicio para operaciones sobre usuarios autenticados."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = UserRepository(session)

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Obtiene un usuario por su ID."""
        return await self.repo.get_by_id(user_id)

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        """
        Actualiza el perfil de un usuario.

        Raises:
            ValueError: Si el nuevo username ya está en uso.
        """
        update_data: dict = {}

        if data.username is not None and data.username != user.username:
            existing = await self.repo.get_by_username(data.username)
            if existing:
                raise ValueError("El username ya está en uso.")
            update_data["username"] = data.username

        if data.password is not None:
            update_data["hashed_password"] = hash_password(data.password)

        if not update_data:
            return user  # Sin cambios

        return await self.repo.update(user, update_data)

    async def deactivate(self, user: User) -> User:
        """Desactiva una cuenta (soft delete)."""
        return await self.repo.update(user, {"is_active": False})

    async def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Lista usuarios (solo para admins). Con paginación offset/limit."""
        return await self.repo.list_all(skip=skip, limit=limit)
