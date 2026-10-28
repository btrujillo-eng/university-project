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

    async def get_restore_code_by_id(
        self, code_id: int
    ) -> RestoreCodeForUpdatePassword | None:
        # Lock the row until the surrounding Unit of Work commits or rolls back.
        # This prevents concurrent password-reset requests from both validating
        # the same code before either one consumes it.
        stmt = (
            select(RestoreCode)
            .where(RestoreCode.id == code_id)
            .with_for_update()
        )
        restore_code = await self.db_session.scalar(stmt)
        if restore_code is None:
            return None

        return RestoreCodeForUpdatePassword(
            user_id=restore_code.user_id,
            code_hash=restore_code.code_hash,
            was_used=restore_code.was_used,
            is_active=restore_code.is_active,
            expired_at=restore_code.expired_at,
        )

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
        # The expiry predicate is repeated in the UPDATE so a code that expires
        # after it was read cannot be consumed successfully.
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
        restore_code = RestoreCode(
            user_id=restore_data.user_id,
            code_hash=restore_data.code_hash,
            expired_at=restore_data.expired_at,
        )
        try:
            self.db_session.add(restore_code)
            await self.db_session.flush()
            # Use the persisted foreign-key value directly. Accessing
            # restore_code.user.id can trigger async lazy-loading (MissingGreenlet).
            return GeneratedRestoreCode(
                code_id=restore_code.id,
                user_id=restore_code.user_id,
            )
        except IntegrityError as e:
            sqlstate = getattr(e.orig, "sqlstate", None) or getattr(
                e.orig, "pgcode", None
            )
            if sqlstate == "23505":
                raise ThereIsAnActiveRestoreCodeError(
                    "A restoration code already exists in active state"
                ) from e
            raise
