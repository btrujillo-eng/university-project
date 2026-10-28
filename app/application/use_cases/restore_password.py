from datetime import UTC, datetime, timedelta

from app.domain.password_code import generate_restore_code
from app.domain.ports import IHasher, IRestoreCodeNotifier, IUnitOfWork
from app.exceptions import (
    RepositoryNotInitializedError,
    RestorationCodeHasAlreadyExpiredError,
    RestoreCodeHasAlreadyBeenUsedError,
    RestoreCodeIsInactive,
    RestoreCodeNotFoundError,
    RestoreCodesDoNotMatchError,
    UnitWorkIsInactiveError,
    UserDoesNotExistError,
)
from app.infrastructure.dtos import RestoreCodeData, UpdatedUserInfo


class PasswordRestorationUseCase:
    def __init__(
        self,
        uow: IUnitOfWork,
        hasher: IHasher,
        notifier: IRestoreCodeNotifier,
    ) -> None:
        self.uow = uow
        self.hasher = hasher
        self.notifier = notifier

    async def create_restore_code(self, email: str) -> None:
        async with self.uow as uow:
            if uow.user is None or uow.restore_code is None:
                raise RepositoryNotInitializedError(
                    "The user or restore-code repository is not initialized"
                )
            user = await uow.user.get_user_by_email(email)
            if user is None:
                # The endpoint returns the same public response whether or not
                # the email exists, preventing account enumeration.
                return
            code = generate_restore_code(4)
            created = await uow.restore_code.add_restore_code(
                RestoreCodeData(
                    user_id=user.user_id,
                    code_hash=self.hasher.apply_hash(code),
                    expired_at=datetime.now(UTC) + timedelta(minutes=10),
                )
            )
            await uow.commit()

        try:
            await self.notifier.send_restore_code(email, code)
        except Exception:
            async with self.uow as uow:
                if uow.restore_code is None:
                    raise RepositoryNotInitializedError(
                        "The restore-code repository is not initialized"
                    )
                await uow.restore_code.desactivate_restore_code(created.code_id)
                await uow.commit()
            raise

    async def _validated_code(
        self,
        user_id: int,
        code_id: int,
        code: str,
    ):
        if self.uow.restore_code is None:
            raise RepositoryNotInitializedError(
                "The restore-code repository is not initialized"
            )
        found = await self.uow.restore_code.get_latest_active_restore_code(user_id)
        if found is None:
            raise RestoreCodeNotFoundError("No active restore code was found")
        actual_code_id, restore_code = found
        if actual_code_id != code_id:
            raise RestoreCodeNotFoundError("Restore code was not found")
        if restore_code.was_used:
            raise RestoreCodeHasAlreadyBeenUsedError("Restore code has already been used")
        if not restore_code.is_active:
            raise RestoreCodeIsInactive("Restore code is inactive")
        if restore_code.expired_at <= datetime.now(UTC):
            raise RestorationCodeHasAlreadyExpiredError("Restore code has expired")
        if not self.hasher.check_hash(restore_code.code_hash, code):
            raise RestoreCodesDoNotMatchError("Restore code does not match")
        return restore_code

    async def verify_restore_code(self, email: str, code: str) -> bool:
        async with self.uow as uow:
            if uow.user is None or uow.restore_code is None:
                raise RepositoryNotInitializedError(
                    "The user or restore-code repository is not initialized"
                )
            user = await uow.user.get_user_by_email(email)
            if user is None:
                raise RestoreCodeNotFoundError("Restore code was not found")
            found = await uow.restore_code.get_latest_active_restore_code(user.user_id)
            if found is None:
                raise RestoreCodeNotFoundError("Restore code was not found")
            _, restore_code = found
            if restore_code.was_used:
                raise RestoreCodeHasAlreadyBeenUsedError("Restore code has already been used")
            if not restore_code.is_active:
                raise RestoreCodeIsInactive("Restore code is inactive")
            if restore_code.expired_at <= datetime.now(UTC):
                raise RestorationCodeHasAlreadyExpiredError("Restore code has expired")
            if not self.hasher.check_hash(restore_code.code_hash, code):
                raise RestoreCodesDoNotMatchError("Restore code does not match")
            return True

    async def update_password(
        self, email: str, new_password: str, code: str
    ) -> UpdatedUserInfo:
        async with self.uow as uow:
            if uow.user is None or uow.restore_code is None:
                raise RepositoryNotInitializedError(
                    "The user or restore-code repository is not initialized"
                )
            user = await uow.user.get_user_by_email_for_update(email)
            if user is None:
                raise UserDoesNotExistError("User does not exist")
            found = await uow.restore_code.get_latest_active_restore_code(user.user_id)
            if found is None:
                raise RestoreCodeNotFoundError("Restore code was not found")
            code_id, restore_code = found
            if restore_code.was_used:
                raise RestoreCodeHasAlreadyBeenUsedError("Restore code has already been used")
            if not restore_code.is_active:
                raise RestoreCodeIsInactive("Restore code is inactive")
            if restore_code.expired_at <= datetime.now(UTC):
                raise RestorationCodeHasAlreadyExpiredError("Restore code has expired")
            if not self.hasher.check_hash(restore_code.code_hash, code):
                raise RestoreCodesDoNotMatchError("Restore code does not match")

            consumed = await uow.restore_code.mark_restore_code_as_used(code_id)
            if not consumed:
                raise RestoreCodeHasAlreadyBeenUsedError(
                    "Restore code was consumed by another request or expired"
                )
            updated = await uow.user.update_password(
                user.user_id, self.hasher.apply_hash(new_password)
            )
            await uow.commit()
            return updated
