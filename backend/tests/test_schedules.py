"""Tests for schedule CRUD and validation."""

import pytest
from unittest.mock import patch

from app.core.auth import hash_password
from app.models.schedule import Schedule
from app.models.user import User


@pytest.mark.asyncio
async def test_list_schedules_empty(client, auth_headers):
    response = await client.get("/api/schedules", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_schedule(client, auth_headers):
    response = await client.post("/api/schedules", headers=auth_headers, json={
        "brand": "Nike",
        "competitors": ["Adidas"],
        "interval_days": 7,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["brand"] == "Nike"
    assert data["competitors"] == ["Adidas"]
    assert data["interval_days"] == 7
    assert data["active"] is True


@pytest.mark.asyncio
async def test_create_schedule_unknown_model(client, auth_headers):
    response = await client.post("/api/schedules", headers=auth_headers, json={
        "brand": "Nike",
        "models": ["nonexistent-model"],
    })
    assert response.status_code == 400
    assert "Unknown model" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_schedule_no_api_key(client, mock_mongo):
    """User without API keys cannot create a schedule."""
    user = User(name="NoKey", email="nokey@example.com", hashed_password=hash_password("password123"))
    await mock_mongo.users.insert_one(user.to_doc())

    from app.core.auth import create_access_token
    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post("/api/schedules", headers=headers, json={
        "brand": "Nike",
    })
    assert response.status_code == 400
    assert "API key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_schedules_returns_created(client, auth_headers):
    await client.post("/api/schedules", headers=auth_headers, json={
        "brand": "Tesla",
        "interval_days": 14,
    })
    response = await client.get("/api/schedules", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["brand"] == "Tesla"


@pytest.mark.asyncio
async def test_delete_schedule(client, auth_headers, mock_mongo, test_user):
    schedule = Schedule(user_id=test_user.id, brand="Nike")
    await mock_mongo.schedules.insert_one(schedule.to_doc())

    response = await client.delete(f"/api/schedules/{schedule.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["ok"] is True

    # Deleted schedule should not appear in list
    response = await client.get("/api/schedules", headers=auth_headers)
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_delete_schedule_not_found(client, auth_headers):
    response = await client.delete("/api/schedules/nonexistent", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_schedule_isolation(client, auth_headers, mock_mongo, test_user):
    """Schedules from other users should not be visible."""
    other = User(name="Other", email="other@example.com", hashed_password=hash_password("password123"))
    await mock_mongo.users.insert_one(other.to_doc())

    schedule = Schedule(user_id=other.id, brand="Secret")
    await mock_mongo.schedules.insert_one(schedule.to_doc())

    response = await client.get("/api/schedules", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_delete_other_users_schedule(client, auth_headers, mock_mongo):
    """Cannot delete another user's schedule."""
    other = User(name="Other", email="other@example.com", hashed_password=hash_password("password123"))
    await mock_mongo.users.insert_one(other.to_doc())

    schedule = Schedule(user_id=other.id, brand="Secret")
    await mock_mongo.schedules.insert_one(schedule.to_doc())

    response = await client.delete(f"/api/schedules/{schedule.id}", headers=auth_headers)
    assert response.status_code == 404
