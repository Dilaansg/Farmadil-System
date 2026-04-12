"""
app/api/v1/__init__.py — Router principal de la versión 1 de la API.
Aquí se agregan todos los sub-routers de /api/v1/.
"""
from fastapi import APIRouter
from app.api.v1.routes import auth, users, products, sales, purchases, catalog

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(products.router)
api_v1_router.include_router(sales.router)
api_v1_router.include_router(purchases.router)
api_v1_router.include_router(catalog.router)
