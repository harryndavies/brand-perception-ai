import pytest


@pytest.mark.asyncio
async def test_signup(client):
    response = await client.post("/api/auth/signup", json={
        "name": "New User",
        "email": "new@example.com",
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "new@example.com"
    assert data["user"]["name"] == "New User"
    assert "token" in data


@pytest.mark.asyncio
async def test_signup_duplicate_email(client, test_user):
    response = await client.post("/api/auth/signup", json={
        "name": "Duplicate",
        "email": "test@example.com",
        "password": "password123",
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login(client, test_user):
    response = await client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "test@example.com"
    assert "token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_user):
    response = await client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    response = await client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "password123",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me(client, auth_headers):
    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_me_no_token(client):
    response = await client.get("/api/auth/me")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_invalid_token(client):
    response = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
