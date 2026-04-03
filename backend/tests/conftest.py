import json

import pytest
from unittest.mock import MagicMock
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient

from app.core.auth import create_access_token, hash_password
from app.core import database, progress
from app.core.encryption import encrypt
from app.models.user import User


def _make_mock_redis():
    """Create a dict-backed mock Redis that supports pipeline()."""
    store = {}
    mock_r = MagicMock()
    mock_r.get.side_effect = lambda k: store.get(k)
    mock_r.set.side_effect = lambda k, v, **kw: store.__setitem__(k, v)
    mock_r.setex.side_effect = lambda k, t, v: store.__setitem__(k, v)
    mock_r.delete.side_effect = lambda k: store.pop(k, None)
    mock_r.incr.side_effect = lambda k: store.__setitem__(k, store.get(k, 0) + 1) or store[k]
    mock_r.expire.return_value = True
    mock_r.publish.return_value = 0

    def _make_pipeline(**kwargs):
        """Return a mock pipeline that records and replays operations."""
        pipe = MagicMock()
        ops = []
        pipe.incr.side_effect = lambda k: ops.append(("incr", k))
        pipe.expire.side_effect = lambda k, t: ops.append(("expire", k, t))

        def execute():
            results = []
            for op in ops:
                if op[0] == "incr":
                    store[op[1]] = store.get(op[1], 0) + 1
                    results.append(store[op[1]])
                elif op[0] == "expire":
                    results.append(True)
            ops.clear()
            return results

        pipe.execute.side_effect = execute
        return pipe

    mock_r.pipeline.side_effect = _make_pipeline
    return mock_r, store


@pytest.fixture(autouse=True)
async def mock_mongo():
    """Replace the real MongoDB client with mongomock for all tests."""
    mock_client = AsyncMongoMockClient()
    mock_db = mock_client["test_perception"]

    # Inject mock db into the database module
    database._test_db = mock_db
    yield mock_db
    database._test_db = None


@pytest.fixture(autouse=True)
def mock_redis():
    """Replace the real Redis client with an in-memory dict for all tests."""
    mock_r, _store = _make_mock_redis()

    original = progress._redis
    progress._redis = mock_r
    yield mock_r
    progress._redis = original


@pytest.fixture(name="client")
async def client_fixture():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(name="test_user")
async def test_user_fixture(mock_mongo):
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hash_password("password123"),
        encrypted_api_key=encrypt("sk-ant-test-key"),
    )
    await mock_mongo.users.insert_one(user.to_doc())
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(test_user):
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}
