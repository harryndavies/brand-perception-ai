from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.core.auth import create_access_token, get_current_user, hash_password, verify_password
from app.core.database import get_async_db
from app.core.encryption import encrypt
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

PROVIDERS = ("anthropic", "openai", "google")


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    team: str
    has_api_key: bool = False
    api_keys: list[str] = []  # list of provider names with keys set


class AuthResponse(BaseModel):
    user: UserResponse
    token: str


@router.post("/signup", response_model=AuthResponse)
async def signup(body: SignupRequest):
    db = get_async_db()

    existing = await db.users.find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    await db.users.insert_one(user.to_doc())

    token = create_access_token(user.id)
    return AuthResponse(
        user=_user_response(user),
        token=token,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    db = get_async_db()

    doc = await db.users.find_one({"email": body.email})
    if not doc or not verify_password(body.password, doc["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user = User.from_doc(doc)
    token = create_access_token(user.id)
    return AuthResponse(
        user=_user_response(user),
        token=token,
    )


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return _user_response(user)


class ApiKeyRequest(BaseModel):
    provider: Literal["anthropic", "openai", "google"]
    api_key: str = Field(..., min_length=1, max_length=200)


@router.put("/api-key")
async def set_api_key(body: ApiKeyRequest, user: User = Depends(get_current_user)):
    db = get_async_db()
    encrypted = encrypt(body.api_key)
    await db.users.update_one(
        {"_id": user.id},
        {"$set": {f"api_keys.{body.provider}": encrypted}},
    )
    from app.core.progress import _get_redis
    _get_redis().delete(f"user:{user.id}")
    return {"provider": body.provider, "saved": True}


@router.delete("/api-key/{provider}")
async def delete_api_key(
    provider: Literal["anthropic", "openai", "google"],
    user: User = Depends(get_current_user),
):
    db = get_async_db()
    await db.users.update_one(
        {"_id": user.id},
        {"$unset": {f"api_keys.{provider}": ""}},
    )
    from app.core.progress import _get_redis
    _get_redis().delete(f"user:{user.id}")
    return {"provider": provider, "removed": True}


def _user_response(user: User) -> UserResponse:
    # Support both legacy single key and new multi-key
    provider_list = list(user.api_keys.keys())
    has_key = len(provider_list) > 0 or user.encrypted_api_key is not None
    if user.encrypted_api_key and "anthropic" not in provider_list:
        provider_list.append("anthropic")
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        team=user.team,
        has_api_key=has_key,
        api_keys=provider_list,
    )
