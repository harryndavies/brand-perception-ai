import pytest
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient

from app.core.auth import create_access_token, hash_password
from app.core import database
from app.core.encryption import encrypt
from app.models.user import User


@pytest.fixture(autouse=True)
async def mock_mongo():
    """Replace the real MongoDB client with mongomock for all tests."""
    mock_client = AsyncMongoMockClient()
    mock_db = mock_client["test_perception"]

    # Inject mock db into the database module
    database._test_db = mock_db
    yield mock_db
    database._test_db = None


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
