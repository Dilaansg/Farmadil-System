"""
app/tests/integration/test_auth.py
────────────────────────────────────
Tests de integración para los endpoints de autenticación.
Usan la BD de testing (SQLite en memoria) y el cliente HTTP async.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass1",
                "username": "testuser",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "hashed_password" not in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {"email": "dup@example.com", "password": "SecurePass1"}
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 400

    async def test_register_weak_password(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "weak@example.com", "password": "simple"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        # Primero registrar
        await client.post(
            "/api/v1/auth/register",
            json={"email": "login@example.com", "password": "SecurePass1"},
        )
        # Luego login
        response = await client.post(
            "/api/v1/auth/login",
            data={"email": "login@example.com", "password": "SecurePass1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "loginwrong@example.com", "password": "SecurePass1"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            data={"email": "loginwrong@example.com", "password": "WrongPass1"},
        )
        assert response.status_code == 400

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            data={"email": "ghost@example.com", "password": "SecurePass1"},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
class TestProtectedEndpoints:
    async def test_get_me_without_token(self, client: AsyncClient):
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 403  # HTTPBearer returns 403 when no token

    async def test_get_me_with_valid_token(self, client: AsyncClient):
        # Registrar y loguear
        await client.post(
            "/api/v1/auth/register",
            json={"email": "me@example.com", "password": "SecurePass1"},
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"email": "me@example.com", "password": "SecurePass1"},
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "me@example.com"
