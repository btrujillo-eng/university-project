import logging

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports import IRestoreCodeRepository
from app.exceptions import ThereIsAnActiveRestoreCodeError
from app.infrastructure.dtos import (
    GeneratedRestoreCode,
    RestoreCodeData,
    RestoreCodeForUpdatePassword,
)
from app.infrastructure.persistence.models import RestoreCode

logger = logging.getLogger(__name__)


class RestoreCodeRepository(IRestoreCodeRepository):
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    @staticmethod
    def _to_dto(record: RestoreCode) -> RestoreCodeForUpdatePassword:
        return RestoreCodeForUpdatePassword(
            user_id=record.user_id,
            code_hash=record.code_hash,
            was_used=record.was_used,
            is_active=record.is_active,
            expired_at=record.expired_at,
        )

    async def get_restore_code_by_id(
        self, code_id: int
    ) -> RestoreCodeForUpdatePassword | None:
        stmt = select(RestoreCode).where(RestoreCode.id == code_id).with_for_update()
        record = await self.db_session.scalar(stmt)
        return self._to_dto(record) if record is not None else None

    async def get_latest_active_restore_code(
        self, user_id: int
    ) -> tuple[int, RestoreCodeForUpdatePassword] | None:
        stmt = (
            select(RestoreCode)
            .where(
                RestoreCode.user_id == user_id,
                RestoreCode.is_active.is_(True),
                RestoreCode.was_used.is_(False),
            )
            .order_by(RestoreCode.id.desc())
            .limit(1)
            .with_for_update()
        )
        record = await self.db_session.scalar(stmt)
        if record is None:
            return None
        return record.id, self._to_dto(record)

    async def desactivate_restore_code(self, code_id: int) -> bool:
        stmt = (
            update(RestoreCode)
            .where(
                RestoreCode.id == code_id,
                RestoreCode.is_active.is_(True),
                RestoreCode.was_used.is_(False),
            )
            .values(is_active=False)
        )
        result = await self.db_session.execute(stmt)
        return bool(result.rowcount)

    async def mark_restore_code_as_used(self, code_id: int) -> bool:
        stmt = (
            update(RestoreCode)
            .where(
                RestoreCode.id == code_id,
                RestoreCode.was_used.is_(False),
                RestoreCode.is_active.is_(True),
                RestoreCode.expired_at > func.now(),
            )
            .values(was_used=True, is_active=False)
        )
        result = await self.db_session.execute(stmt)
        return bool(result.rowcount)

    async def add_restore_code(
        self, restore_data: RestoreCodeData
    ) -> GeneratedRestoreCode:
        # Deactivate prior codes before inserting a replacement. This keeps the
        # latest-code lookup unambiguous even without a database partial index.
        await self.db_session.execute(
            update(RestoreCode)
            .where(
                RestoreCode.user_id == restore_data.user_id,
                RestoreCode.is_active.is_(True),
                RestoreCode.was_used.is_(False),
            )
            .values(is_active=False)
        )
        record = RestoreCode(
            user_id=restore_data.user_id,
            code_hash=restore_data.code_hash,
            expired_at=restore_data.expired_at,
        )
        try:
            self.db_session.add(record)
            await self.db_session.flush()
            return GeneratedRestoreCode(code_id=record.id, user_id=record.user_id)
        except IntegrityError as exc:
            sqlstate = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
            if sqlstate == "23505":
                raise ThereIsAnActiveRestoreCodeError(
                    "A restoration code already exists in active state"
                ) from exc
            raise
