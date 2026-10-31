from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.user_registration import get_register_user
from app.api.schemas import UserCreateRequest, UserRegistrationResponse
from app.application import RegisterUserUseCase
from app.domain.enums import UserRole
from app.exceptions import (
    EmailAlreadyExistsError,
    RepositoryNotInitializedError,
    UnitWorkIsInactiveError,
)
from app.infrastructure.dtos import RegisterUserData

router = APIRouter(prefix="/register", tags=["registration"])


@router.post("/user/", response_model=UserRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreateRequest,
    repository: RegisterUserUseCase = Depends(get_register_user),
) -> UserRegistrationResponse:
    try:
        to_register = RegisterUserData(
            first_name=user_data.first_name,
            middle_name=user_data.middle_name,
            first_surname=user_data.first_surname,
            middle_surname=user_data.middle_surname,
            email=str(user_data.contact_info.email),
            password=user_data.password.get_secret_value(),
            # Public registration must never let a caller assign privileged roles.
            user_role=UserRole.CUSTOMER.value,
        )
        user = await repository.register(to_register)
        return UserRegistrationResponse(
            user_id=user.user_id,
            first_name=user.first_name,
            first_surname=user.first_surname,
            user_role=UserRole(user.user_role),
            is_active=user.is_active,
            message="Registro exitoso. Ya puedes iniciar sesión en el sistema!",
        )
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ingresado ya existe en el sistema.",
        )
    except (RepositoryNotInitializedError, UnitWorkIsInactiveError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de registros de usuario está temporalmente fuera de servicio.",
        )
