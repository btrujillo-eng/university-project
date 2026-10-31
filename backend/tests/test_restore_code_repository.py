import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.infrastructure.dtos import RestoreCodeData
from app.infrastructure.persistence.repositories.postgresql.restore_code import (
    RestoreCodeRepository,
)


class FakeSession:
    def __init__(self, *, record=None, rowcount=1):
        self.record = record
        self.rowcount = rowcount
        self.added = None
        self.statement = None

    async def scalar(self, statement):
        self.statement = statement
        return self.record

    def add(self, instance):
        self.added = instance

    async def flush(self):
        self.added.id = 23

    async def execute(self, statement):
        self.statement = statement
        return SimpleNamespace(rowcount=self.rowcount)


def test_add_restore_code_uses_foreign_key_without_lazy_relationship_access():
    session = FakeSession()
    repository = RestoreCodeRepository(session)
    data = RestoreCodeData(
        user_id=7,
        code_hash="hashed-code",
        expired_at=datetime.now(UTC) + timedelta(minutes=10),
    )

    result = asyncio.run(repository.add_restore_code(data))

    assert result.code_id == 23
    assert result.user_id == 7
    assert session.added.user_id == 7


def test_get_restore_code_by_id_returns_persistence_dto():
    record = SimpleNamespace(
        id=23,
        user_id=7,
        code_hash="hashed-code",
        was_used=False,
        is_active=True,
        expired_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    session = FakeSession(record=record)
    repository = RestoreCodeRepository(session)

    result = asyncio.run(repository.get_restore_code_by_id(23))

    assert result is not None
    assert result.user_id == 7
    assert result.code_hash == "hashed-code"
    assert result.was_used is False
    assert result.is_active is True
    assert "FOR UPDATE" in str(session.statement).upper()


def test_mark_restore_code_as_used_reports_whether_a_row_was_consumed():
    repository = RestoreCodeRepository(FakeSession(rowcount=0))
    result = asyncio.run(repository.mark_restore_code_as_used(23))
    assert result is False

    repository = RestoreCodeRepository(FakeSession(rowcount=1))
    result = asyncio.run(repository.mark_restore_code_as_used(23))
    assert result is True
