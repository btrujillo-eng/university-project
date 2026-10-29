from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.id_token import verify_oauth2_token
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from jwt import InvalidTokenError, decode

from app.api.dependencies.user_auth import (
    get_authenticate_user,
    get_user_repository,
)
from app.api.schemas import GoogleLoginRequest, Token, UserResponse
from app.application import AuthenticateUserUseCase
from app.domain.enums import UserRole
from app.exceptions import AuthenticateUserError, UserIsNotActiveError
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.database_engine import AsyncSessionLocal
from app.infrastructure.dtos import AuthenticatedUser, GoogleUserData
from app.infrastructure.unit_of_work import UnitOfWork
from app.infrastructure.jwt_handler import create_access_token
from app.infrastructure.persistence.repositories.postgresql import UserRepository


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/v1/auth/token")

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudieron validar las credenciales",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    repository: Annotated[UserRepository, Depends(get_user_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> AuthenticatedUser:
    try:
        payload = decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject.isdecimal():
            raise CREDENTIALS_EXCEPTION
        user_id = int(subject)
        if user_id <= 0:
            raise CREDENTIALS_EXCEPTION
    except (InvalidTokenError, TypeError, ValueError):
        raise CREDENTIALS_EXCEPTION from None

    user = await repository.get_user_by_id(user_id)
    if user is None:
        raise CREDENTIALS_EXCEPTION

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu usuario está inactivo. Por favor, contacta con soporte.",
        )

    return AuthenticatedUser(
        user_id=user.user_id,
        first_name=user.first_name,
        first_surname=user.first_surname,
        user_role=user.user_role,
        is_active=user.is_active,
    )


router_login = APIRouter(prefix="/users", tags=["token"])


@router_login.post("/v1/auth/google", response_model=Token)
async def login_with_google(
    request_data: GoogleLoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Token:
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El inicio de sesión con Google no está configurado.",
        )

    try:
        claims = await run_in_threadpool(
            verify_oauth2_token,
            request_data.id_token,
            GoogleRequest(),
            settings.google_client_id,
        )
    except (ValueError, GoogleAuthError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token de Google no es válido.",
        ) from None

    email = claims.get("email")
    google_sub = claims.get("sub")
    if (
        not isinstance(email, str)
        or not isinstance(google_sub, str)
        or claims.get("email_verified") is not True
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google no confirmó la identidad y el correo de la cuenta.",
        )

    given_name = claims.get("given_name")
    family_name = claims.get("family_name")
    first_name = given_name.strip() if isinstance(given_name, str) else "Google"
    first_surname = family_name.strip() if isinstance(family_name, str) else "Usuario"
    first_name = first_name[:20] or "Google"
    first_surname = first_surname[:20] or "Usuario"

    try:
        async with UnitOfWork(AsyncSessionLocal) as uow:
            assert uow.user is not None
            user = await uow.user.get_user_by_google_sub(google_sub)
            if user is None:
                existing_email_user = await uow.user.get_user_by_email(email)
                if existing_email_user is not None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Ya existe una cuenta con este correo. Inicia sesión "
                            "con tu método habitual antes de vincular Google."
                        ),
                    )
                user = await uow.user.add_google_user(
                    GoogleUserData(
                        email=email,
                        google_sub=google_sub,
                        first_name=first_name,
                        first_surname=first_surname,
                    )
                )
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tu usuario está inactivo. Por favor, contacta con soporte.",
                )
            await uow.commit()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No fue posible crear la cuenta de Google. Inténtalo de nuevo.",
        ) from None

    return Token(access_token=create_access_token(user.user_id))


@router_login.post("/v1/auth/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_user: Annotated[AuthenticateUserUseCase, Depends(get_authenticate_user)],
) -> Token:
    try:
        user = await auth_user.authenticate(form_data.username, form_data.password)
        access_token = create_access_token(user.user_id)
        return Token(access_token=access_token)
    except AuthenticateUserError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except UserIsNotActiveError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu usuario está inactivo. Por favor, contacta con soporte.",
        ) from None


router_home_page = APIRouter(prefix="/me", tags=["users"])


@router_home_page.get("/", response_model=UserResponse)
async def read_user_me(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse(
        user_id=user.user_id,
        first_name=user.first_name,
        first_surname=user.first_surname,
        user_role=UserRole(user.user_role),
        is_active=user.is_active,
    )
