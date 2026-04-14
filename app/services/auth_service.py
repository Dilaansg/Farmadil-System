from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.user import UserLogin, Token
from app.repositories.user_repository import UserRepository
from app.core.security import verify_password, create_access_token, create_refresh_token


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def authenticate_user(self, user_login: UserLogin) -> User | None:
        """Autenticar usuario verificando su email y contraseña."""
        user = await self.user_repo.get_by_email(user_login.email)
        if not user:
            return None
        
        if not verify_password(user_login.password, user.password_hash):
            return None
        
        return user

    def create_token_for_user(self, user: User) -> Token:
        """Generar el token JWT para un usuario válido."""
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Inactive user"
            )
        
        access_token = create_access_token(
            data={"sub": str(user.id), "rol": user.rol.value}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "rol": user.rol.value}
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
