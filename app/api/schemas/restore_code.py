from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


class CreateRestoreCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class CreateRestoreCodeResponse(BaseModel):
    message: str = "Si la cuenta existe, recibirás un código de verificación por correo."


class VerifyRestoreCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    restore_code: str = Field(pattern=r"^\d{4}$")


class UpdatePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    restore_code: str = Field(pattern=r"^\d{4}$")
    new_password: SecretStr = Field(min_length=8, max_length=128)
