"""
app/services/user_service.py
──────────────────────────────
Lógica de negocio para gestión de usuarios.
"""
import uuid
from datetime import datetime, timezone

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
            ValueError: Si el nuevo email ya está en uso.
        """
        if data.email is not None and data.email != user.email:
            existing = await self.repo.get_by_email(data.email)
            if existing:
                raise ValueError("El email ya está en uso por otro usuario.")
            user.email = data.email

        if data.password is not None:
            user.password_hash = hash_password(data.password)

        # Actualizar timestamp de modificación
        user.updated_at = datetime.now(timezone.utc)

        self.repo.session.add(user)
        await self.repo.session.commit()
        await self.repo.session.refresh(user)
        return user

    async def deactivate(self, user: User) -> User:
        """Desactiva una cuenta (soft delete)."""
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        self.repo.session.add(user)
        await self.repo.session.commit()
        await self.repo.session.refresh(user)
        return user

    async def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Lista usuarios (solo para admins). Con paginación offset/limit."""
        return await self.repo.list_all(skip=skip, limit=limit)
