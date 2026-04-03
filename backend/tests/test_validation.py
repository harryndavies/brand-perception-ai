"""Tests for input validation, rate limiting, and security hardening."""

import pytest
from unittest.mock import patch, MagicMock


# -- Input validation ----------------------------------------------------------

@pytest.mark.asyncio
@patch("app.services.report_service.run_analysis")
async def test_create_report_empty_brand(mock_analysis, client, auth_headers):
    """Empty brand should be rejected."""
    response = await client.post("/api/reports", headers=auth_headers, json={
        "brand": "",
        "competitors": [],
    })
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("app.services.report_service.run_analysis")
async def test_create_report_brand_too_long(mock_analysis, client, auth_headers):
    """Brand exceeding 100 chars should be rejected."""
    response = await client.post("/api/reports", headers=auth_headers, json={
        "brand": "A" * 101,
        "competitors": [],
    })
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("app.services.report_service.run_analysis")
async def test_create_report_too_many_competitors(mock_analysis, client, auth_headers):
    """More than 3 competitors should be rejected."""
    response = await client.post("/api/reports", headers=auth_headers, json={
        "brand": "TestBrand",
        "competitors": ["A", "B", "C", "D"],
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_short_password(client):
    """Password under 8 chars should be rejected."""
    response = await client.post("/api/auth/signup", json={
        "name": "Test",
        "email": "short@example.com",
        "password": "abc",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_empty_name(client):
    """Empty name should be rejected."""
    response = await client.post("/api/auth/signup", json={
        "name": "",
        "email": "noname@example.com",
        "password": "password123",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_long_password(client):
    """Password over 128 chars should be rejected."""
    response = await client.post("/api/auth/signup", json={
        "name": "Test",
        "email": "long@example.com",
        "password": "x" * 129,
    })
    assert response.status_code == 422


# -- Rate limiting -------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.services.report_service.run_analysis")
@patch("app.services.rate_limiter._get_redis")
async def test_rate_limit_allows_normal_usage(mock_redis, mock_analysis, client, auth_headers):
    """Normal usage within limit should succeed."""
    mock_r = MagicMock()
    mock_pipe = MagicMock()
    mock_pipe.execute.return_value = [1, True]  # count=1, expire=True
    mock_r.pipeline.return_value = mock_pipe
    mock_redis.return_value = mock_r

    response = await client.post("/api/reports", headers=auth_headers, json={
        "brand": "TestBrand",
        "competitors": [],
    })
    assert response.status_code == 201


@pytest.mark.asyncio
@patch("app.services.report_service.run_analysis")
@patch("app.services.rate_limiter._get_redis")
async def test_rate_limit_blocks_excess(mock_redis, mock_analysis, client, auth_headers):
    """Exceeding rate limit should return 429."""
    mock_r = MagicMock()
    mock_pipe = MagicMock()
    mock_pipe.execute.return_value = [6, True]  # count=6, over the limit of 5
    mock_r.pipeline.return_value = mock_pipe
    mock_redis.return_value = mock_r

    response = await client.post("/api/reports", headers=auth_headers, json={
        "brand": "TestBrand",
        "competitors": [],
    })
    assert response.status_code == 429
    assert "Rate limit" in response.json()["detail"]
