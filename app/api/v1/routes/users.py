"""
app/api/v1/routes/users.py
───────────────────────────
Endpoints de gestión de usuarios.
"""
from fastapi import APIRouter, status

from app.dependencies.auth import CurrentAdmin, CurrentUser
from app.dependencies.db import SessionDep
from app.schemas.user import UserPublic, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Obtener perfil propio",
)
async def get_me(current_user: CurrentUser) -> UserPublic:
    """Retorna el perfil del usuario autenticado."""
    return UserPublic.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserPublic,
    summary="Actualizar perfil propio",
)
async def update_me(
    body: UserUpdate,
    current_user: CurrentUser,
    session: SessionDep,
) -> UserPublic:
    """Actualiza username y/o password del usuario autenticado."""
    service = UserService(session)
    updated = await service.update_profile(current_user, body)
    return UserPublic.model_validate(updated)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desactivar mi cuenta",
)
async def deactivate_me(current_user: CurrentUser, session: SessionDep) -> None:
    """Desactiva la cuenta del usuario autenticado (soft delete)."""
    service = UserService(session)
    await service.deactivate(current_user)


# ── Endpoints de Admin ──────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[UserPublic],
    summary="[Admin] Listar todos los usuarios",
)
async def list_users(
    _admin: CurrentAdmin,
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
) -> list[UserPublic]:
    """Lista todos los usuarios. Solo accesible para superusers."""
    service = UserService(session)
    users = await service.list_users(skip=skip, limit=limit)
    return [UserPublic.model_validate(u) for u in users]
