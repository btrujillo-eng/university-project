from functools import lru_cache

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    stripe_api_key: SecretStr = Field(default=...)
    resend_api_key: SecretStr = Field(default=...)
    resend_from_email: str = "onboarding@resend.dev"
    debug: bool = Field(default=False)
    ddl_db_user: SecretStr = Field(default=...)
    ddl_user_password: SecretStr = Field(default=...)
    dml_db_user: SecretStr = Field(default=...)
    dml_user_password: SecretStr = Field(default=...)
    db_host: SecretStr = Field(default=...)
    db_port: SecretStr = Field(default=...)
    db_name: SecretStr = Field(default=...)
    jwt_secret_key: SecretStr = Field(default=...)
    jwt_algorithm: str = Field(default=...)
    access_token_expire_minutes: int = Field(default=...)
    google_client_id: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @computed_field
    @property
    def async_database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.dml_db_user.get_secret_value(),
            password=self.dml_user_password.get_secret_value(),
            host=self.db_host.get_secret_value(),
            port=int(self.db_port.get_secret_value()),
            database=self.db_name.get_secret_value(),
        )
        
    @computed_field
    @property
    def migrator_db_url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.ddl_db_user.get_secret_value(),
            password=self.ddl_user_password.get_secret_value(),
            host=self.db_host.get_secret_value(),
            port=int(self.db_port.get_secret_value()),
            database=self.db_name.get_secret_value(),
        )

@lru_cache
def get_settings() -> Settings:
    return Settings()
