from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_KNOWN_WEAK_SECRETS = {"change-me-to-a-long-random-string", "changeme", "secret", ""}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_secret: str
    app_password: str

    database_url: str

    ollama_host: str = "http://host.docker.internal:11434"
    ollama_default_model: str = ""
    ollama_timeout_s: int = 300

    log_level: str = "INFO"

    @field_validator("app_secret")
    @classmethod
    def secret_must_be_strong(cls, v: str) -> str:
        if v in _KNOWN_WEAK_SECRETS:
            raise ValueError(
                "APP_SECRET is set to a known default — generate a real secret with: "
                "python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if len(v) < 32:
            raise ValueError("APP_SECRET must be at least 32 characters")
        return v


settings = Settings()
