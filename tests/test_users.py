from unittest.mock import Mock

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_creates_user_and_sends_welcome_email(
    client: AsyncClient, mock_email_sender: Mock
) -> None:
    response = await client.post(
        "/users/register",
        json={"email": "a@example.com", "password": "strongpass123"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "a@example.com"
    assert "hashed_password" not in body  # response_model не віддає службові поля

    mock_email_sender.send.assert_called_once()


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client: AsyncClient) -> None:
    payload = {"email": "dup@example.com", "password": "strongpass123"}
    await client.post("/users/register", json=payload)

    response = await client.post("/users/register", json=payload)

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_and_me(client: AsyncClient) -> None:
    await client.post(
        "/users/register", json={"email": "login@example.com", "password": "strongpass123"}
    )

    login_response = await client.post(
        "/users/login",
        data={"username": "login@example.com", "password": "strongpass123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = await client.get(
        "/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "login@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    await client.post(
        "/users/register", json={"email": "wrong@example.com", "password": "strongpass123"}
    )

    response = await client.post(
        "/users/login",
        data={"username": "wrong@example.com", "password": "totally-wrong"},
    )

    assert response.status_code == 401
