import uuid
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import hash_password


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        """Busca un usuario por su email descartando los que estén borrados."""
        statement = select(User).where(User.email == email, User.is_deleted == False)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str | uuid.UUID) -> User | None:
        """Busca un usuario por su ID descartando los que estén borrados."""
        if isinstance(user_id, str):
            try:
                user_id = uuid.UUID(user_id)
            except ValueError:
                return None

        statement = select(User).where(User.id == user_id, User.is_deleted == False)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, user_in: UserCreate) -> User:
        """Crea un nuevo usuario en la base de datos."""
        user = User(
            email=user_in.email,
            password_hash=hash_password(user_in.password),
            rol=user_in.rol
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Lista todos los usuarios activos con paginación."""
        statement = (
            select(User)
            .where(User.is_deleted == False)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
