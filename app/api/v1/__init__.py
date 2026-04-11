"""
app/api/v1/__init__.py — Router principal de la versión 1 de la API.
Aquí se agregan todos los sub-routers de /api/v1/.
"""
from fastapi import APIRouter

from app.api.v1.routes import auth, users

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
