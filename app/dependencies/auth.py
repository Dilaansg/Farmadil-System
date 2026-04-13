from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.dependencies.db import SessionDep

bearer_scheme = HTTPBearer(auto_error=False)

TokenDep = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]

def get_user_repository(session: SessionDep) -> UserRepository:
    """Inyecta el repositorio de usuarios."""
    return UserRepository(session)

UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


async def get_current_user(
    token: TokenDep,
    user_repo: UserRepositoryDep
) -> User:
    """Extrae y valida el JWT para obtener el usuario autenticado actual."""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token.credentials)
    if not payload:
        raise credentials_exception
        
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception
        
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
        
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


class RoleChecker:
    """
    Middlewares / Dependencia de RBAC.
    Bloquea accesos lanzando HTTP 403 si el usuario no tiene los roles permitidos.
    """
    def __init__(self, allowed_roles: list[str | UserRole]):
        self.allowed_roles = [
            role if isinstance(role, str) else role.value for role in allowed_roles
        ]

    def __call__(self, user: CurrentUser) -> User:
        if user.rol.value not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted"
            )
        return user

def require_role(roles: list[str | UserRole]):
    """Alias para construir la dependencia RoleChecker fácilmente."""
    return Depends(RoleChecker(roles))

CurrentAdmin = Annotated[User, Depends(RoleChecker([UserRole.SUPERADMIN, UserRole.ADMIN]))]
