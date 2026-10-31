import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.application.use_cases.restore_password import PasswordRestorationUseCase
from app.exceptions import RestoreCodesDoNotMatchError, RestorationCodeHasAlreadyExpiredError


class FakeHasher:
    def apply_hash(self, value: str) -> str:
        return f"hashed:{value}"

    def check_hash(self, hashed_text: str, plain_text: str) -> bool:
        return hashed_text == f"hashed:{plain_text}"


class FakeRestoreRepository:
    def __init__(self, record=None):
        self.record = record
        self.consumed = False
        self.deactivated = []

    async def add_restore_code(self, data):
        self.record = SimpleNamespace(
            user_id=data.user_id,
            code_hash=data.code_hash,
            was_used=False,
            is_active=True,
            expired_at=data.expired_at,
        )
        return SimpleNamespace(code_id=41, user_id=data.user_id)

    async def get_restore_code_by_id(self, code_id):
        return self.record

    async def get_latest_active_restore_code(self, user_id):
        return (41, self.record) if self.record is not None else None

    async def mark_restore_code_as_used(self, code_id):
        if self.consumed:
            return False
        self.consumed = True
        return True

    async def desactivate_restore_code(self, code_id):
        self.deactivated.append(code_id)
        return True


class FakeUserRepository:
    def __init__(self, user=None):
        self.user = user
        self.updated = None

    async def get_user_by_email(self, email):
        return self.user

    async def get_user_by_email_for_update(self, email):
        return self.user

    async def update_password(self, user_id, hashed_password):
        self.updated = (user_id, hashed_password)
        return SimpleNamespace(first_name="Test", first_surname="User")


class FakeUow:
    def __init__(self, user, restore):
        self.user = user
        self.restore_code = restore
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollbacks += 1
        return None

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class FakeNotifier:
    def __init__(self):
        self.last_email = None
        self.last_code = None

    async def send_restore_code(self, email, code):
        self.last_email = email
        self.last_code = code


def make_record(*, expired=False, code_hash="hashed:123456", active=True, used=False):
    expiry = datetime.now(UTC) - timedelta(minutes=1) if expired else datetime.now(UTC) + timedelta(minutes=10)
    return SimpleNamespace(
        user_id=7,
        code_hash=code_hash,
        was_used=used,
        is_active=active,
        expired_at=expiry,
    )


def make_use_case(record=None):
    user = SimpleNamespace(user_id=7, is_active=True)
    user_repo = FakeUserRepository(user)
    restore_repo = FakeRestoreRepository(record or make_record())
    uow = FakeUow(user_repo, restore_repo)
    notifier = FakeNotifier()
    return PasswordRestorationUseCase(uow, FakeHasher(), notifier), user_repo, restore_repo, uow, notifier


def test_update_password_consumes_code_and_commits_password_together():
    use_case, user_repo, restore_repo, uow, _ = make_use_case()
    result = asyncio.run(use_case.update_password("test@example.com", "new-password", "123456"))
    assert result.first_name == "Test"
    assert restore_repo.consumed is True
    assert user_repo.updated == (7, "hashed:new-password")
    assert uow.commits == 1


def test_update_password_rejects_wrong_code_without_changing_password():
    use_case, user_repo, _, uow, _ = make_use_case()
    with pytest.raises(RestoreCodesDoNotMatchError):
        asyncio.run(use_case.update_password("test@example.com", "new-password", "999999"))
    assert user_repo.updated is None
    assert uow.commits == 0


def test_update_password_rejects_expired_code():
    use_case, _, _, _, _ = make_use_case(make_record(expired=True))
    with pytest.raises(RestorationCodeHasAlreadyExpiredError):
        asyncio.run(use_case.update_password("test@example.com", "new-password", "123456"))


def test_create_restore_code_does_not_send_for_unknown_email():
    use_case, user_repo, _, uow, notifier = make_use_case()
    user_repo.user = None
    asyncio.run(use_case.create_restore_code("missing@example.com"))
    assert notifier.last_code is None
    assert uow.commits == 0


def test_create_restore_code_sends_email_after_commit():
    use_case, _, restore_repo, uow, notifier = make_use_case()
    asyncio.run(use_case.create_restore_code("test@example.com"))
    assert notifier.last_email == "test@example.com"
    assert notifier.last_code is not None
    assert len(notifier.last_code) == 6
    assert restore_repo.record.code_hash == f"hashed:{notifier.last_code}"
    assert uow.commits == 1
