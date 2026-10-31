from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.restore_password import get_password_restoration_use_case
from app.api.schemas import (
    CreateRestoreCodeRequest,
    CreateRestoreCodeResponse,
    UpdatePasswordRequest,
    VerifyRestoreCodeRequest,
)
from app.application.use_cases.restore_password import PasswordRestorationUseCase
from app.exceptions import (
    NotificationServiceError,
    RepositoryNotInitializedError,
    RestorationCodeHasAlreadyExpiredError,
    RestoreCodeHasAlreadyBeenUsedError,
    RestoreCodeIsInactive,
    RestoreCodeNotFoundError,
    RestoreCodesDoNotMatchError,
    ThereIsAnActiveRestoreCodeError,
    UnitWorkIsInactiveError,
    UserDoesNotExistError,
)

router = APIRouter(prefix="/users/v1/auth/password", tags=["password restoration"])


@router.post("/restore-code", response_model=CreateRestoreCodeResponse)
async def create_restore_code(
    request: CreateRestoreCodeRequest,
    use_case: Annotated[
        PasswordRestorationUseCase, Depends(get_password_restoration_use_case)
    ],
) -> CreateRestoreCodeResponse:
    try:
        await use_case.create_restore_code(str(request.email))
        return CreateRestoreCodeResponse(
            message="Si la cuenta existe, recibirás un código de verificación por correo."
        )
    except ThereIsAnActiveRestoreCodeError:
        # Do not expose whether the address exists or already has a code.
        return CreateRestoreCodeResponse(
            message="Si la cuenta existe, recibirás un código de verificación por correo."
        )
    except NotificationServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible enviar el correo de recuperación. Intenta nuevamente.",
        ) from None
    except (RepositoryNotInitializedError, UnitWorkIsInactiveError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de recuperación está temporalmente fuera de servicio.",
        ) from None


@router.post("/verify")
async def verify_restore_code(
    request: VerifyRestoreCodeRequest,
    use_case: Annotated[
        PasswordRestorationUseCase, Depends(get_password_restoration_use_case)
    ],
) -> dict[str, str]:
    try:
        await use_case.verify_restore_code(str(request.email), request.restore_code)
        return {"message": "Código válido. Puedes crear una nueva contraseña."}
    except RestoreCodeNotFoundError:
        raise HTTPException(status_code=400, detail="El código de verificación es inválido o expiró.") from None
    except RestoreCodesDoNotMatchError:
        raise HTTPException(status_code=400, detail="El código de verificación es inválido o expiró.") from None
    except (RestorationCodeHasAlreadyExpiredError, RestoreCodeHasAlreadyBeenUsedError, RestoreCodeIsInactive):
        raise HTTPException(status_code=400, detail="El código de verificación es inválido o expiró.") from None
    except (RepositoryNotInitializedError, UnitWorkIsInactiveError):
        raise HTTPException(status_code=503, detail="El servicio de recuperación no está disponible.") from None


@router.post("/reset")
async def reset_password(
    request: UpdatePasswordRequest,
    use_case: Annotated[
        PasswordRestorationUseCase, Depends(get_password_restoration_use_case)
    ],
) -> dict[str, str]:
    try:
        updated = await use_case.update_password(
            email=str(request.email),
            new_password=request.new_password.get_secret_value(),
            code=request.restore_code,
        )
        return {"message": f"La contraseña de {updated.first_name} fue actualizada correctamente."}
    except (RestoreCodeNotFoundError, UserDoesNotExistError):
        raise HTTPException(status_code=400, detail="El código de verificación es inválido o expiró.") from None
    except RestoreCodesDoNotMatchError:
        raise HTTPException(status_code=400, detail="El código de verificación es inválido o expiró.") from None
    except (RestorationCodeHasAlreadyExpiredError, RestoreCodeHasAlreadyBeenUsedError, RestoreCodeIsInactive):
        raise HTTPException(status_code=400, detail="El código de verificación es inválido o expiró.") from None
    except (RepositoryNotInitializedError, UnitWorkIsInactiveError):
        raise HTTPException(status_code=503, detail="El servicio de recuperación no está disponible.") from None
