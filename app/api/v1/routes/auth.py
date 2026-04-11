from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.user import Token, UserPublic, UserCreate, UserLogin
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
from app.dependencies.auth import get_user_repository, CurrentUser

router = APIRouter(prefix="/auth", tags=["Autenticación"])

def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)]
) -> AuthService:
    """Inyecta el servicio de autenticación con el repositorio configurado."""
    return AuthService(user_repo)

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthServiceDep
):
    """
    Endpoint para intercambiar credenciales por JWT Token.
    Cumple con el estándar OAuth2 usando Content-Type: application/x-www-form-urlencoded
    """
    user_login = UserLogin(email=form_data.username, password=form_data.password)
    user = await auth_service.authenticate_user(user_login)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return auth_service.create_token_for_user(user)


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    auth_service: AuthServiceDep
):
    """
    Endpoint de utilidad para registrar nuevos usuarios.
    """
    user_exists = await auth_service.user_repo.get_by_email(user_in.email)
    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system."
        )
        
    user = await auth_service.user_repo.create(user_in)
    return user


@router.get("/me", response_model=UserPublic)
async def get_me(user: CurrentUser):
    """
    Retorna la información del usuario en sesión actualmente.
    """
    return user
