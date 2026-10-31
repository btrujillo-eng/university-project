import pytest
from pydantic import ValidationError

from app.api.schemas import UserCreateRequest, UserRegistrationResponse
from app.domain.enums import UserRole


def valid_registration_payload() -> dict[str, object]:
    return {
        "first_name": "Brayan",
        "first_surname": "Trujillo",
        "contact_info": {"email": "brayan@example.com"},
        "password": "A-strong-password-123",
    }


def test_registration_request_accepts_required_registration_data() -> None:
    request = UserCreateRequest.model_validate(valid_registration_payload())

    assert request.first_name == "Brayan"
    assert str(request.contact_info.email) == "brayan@example.com"


def test_registration_request_rejects_client_supplied_role() -> None:
    payload = valid_registration_payload()
    payload["user_role"] = UserRole.STORE_MANAGER.value

    with pytest.raises(ValidationError):
        UserCreateRequest.model_validate(payload)


def test_registration_response_includes_success_message_and_customer_role() -> None:
    response = UserRegistrationResponse(
        user_id=1,
        first_name="Brayan",
        first_surname="Trujillo",
        user_role=UserRole.CUSTOMER,
        is_active=True,
    )

    assert response.message == "Registro exitoso. Ya puedes iniciar sesión en el sistema!"
    assert response.user_role is UserRole.CUSTOMER
