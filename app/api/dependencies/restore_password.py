from fastapi import Depends

from app.application.use_cases.restore_password import PasswordRestorationUseCase
from app.domain.ports import IRestoreCodeNotifier
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.database_engine import AsyncSessionLocal
from app.infrastructure.hasher import Hasher
from app.infrastructure.notifications.restore_code_notifier import ResendRestoreCodeNotifier
from app.infrastructure.unit_of_work import UnitOfWork


def get_restore_code_notifier(
    settings: Settings = Depends(get_settings),
) -> IRestoreCodeNotifier:
    return ResendRestoreCodeNotifier(settings)


def get_password_restoration_use_case(
    notifier: IRestoreCodeNotifier = Depends(get_restore_code_notifier),
) -> PasswordRestorationUseCase:
    return PasswordRestorationUseCase(
        uow=UnitOfWork(AsyncSessionLocal),
        hasher=Hasher(),
        notifier=notifier,
    )
