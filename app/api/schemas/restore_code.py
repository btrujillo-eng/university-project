from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


class CreateRestoreCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(description="Email registered in the system")


class CreateRestoreCodeResponse(BaseModel):
    code_id: int = Field(description="Identifier used to validate the restore code")
    message: str = "If the account exists, a verification code will be sent to its email."


class VerifyRestoreCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code_id: int = Field(gt=0)
    restore_code: str = Field(pattern=r"^\d{4}$")


class UpdatePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(gt=0)
    code_id: int = Field(gt=0)
    restore_code: str = Field(pattern=r"^\d{4}$")
    new_password: SecretStr = Field(min_length=8, max_length=128)
