import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.api.v1.routers.user_auth import get_current_user
from app.infrastructure.dtos import UserForAuthentication


SECRET = "test-secret-for-unit-tests-only"


class FakeUserRepository:
    def __init__(self, user: UserForAuthentication | None) -> None:
        self.user = user
        self.requested_user_id: int | None = None

    async def get_user_by_id(self, user_id: int) -> UserForAuthentication | None:
        self.requested_user_id = user_id
        return self.user


def make_token(payload: dict[str, object]) -> str:
    return jwt.encode(payload, SECRET, algorithm="HS256")


def make_settings() -> SimpleNamespace:
    return SimpleNamespace(jwt_secret_key=SecretStr(SECRET), jwt_algorithm="HS256")


def active_user(*, is_active: bool = True) -> UserForAuthentication:
    return UserForAuthentication(
        user_id=7,
        first_name="Test",
        first_surname="User",
        password_hash="not-used-in-this-test",
        user_role="customer",
        is_active=is_active,
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"sub": "7"},
        {"exp": datetime.now(UTC) + timedelta(minutes=5)},
    ],
)
def test_current_user_rejects_token_missing_required_claims(
    payload: dict[str, object],
) -> None:
    repository = FakeUserRepository(active_user())
    token = make_token(payload)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_user(repository, make_settings(), token))

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
    assert repository.requested_user_id is None


@pytest.mark.parametrize("subject", ["not-a-number", "0", "-2"])
def test_current_user_rejects_invalid_subject(subject: str) -> None:
    repository = FakeUserRepository(active_user())
    token = make_token(
        {"sub": subject, "exp": datetime.now(UTC) + timedelta(minutes=5)}
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_user(repository, make_settings(), token))

    assert exc_info.value.status_code == 401
    assert repository.requested_user_id is None


def test_current_user_returns_authenticated_user_for_valid_token() -> None:
    repository = FakeUserRepository(active_user())
    token = make_token(
        {"sub": "7", "exp": datetime.now(UTC) + timedelta(minutes=5)}
    )

    result = asyncio.run(get_current_user(repository, make_settings(), token))

    assert result.user_id == 7
    assert result.first_name == "Test"
    assert repository.requested_user_id == 7


def test_current_user_rejects_inactive_account() -> None:
    repository = FakeUserRepository(active_user(is_active=False))
    token = make_token(
        {"sub": "7", "exp": datetime.now(UTC) + timedelta(minutes=5)}
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_user(repository, make_settings(), token))

    assert exc_info.value.status_code == 403
    assert repository.requested_user_id == 7
