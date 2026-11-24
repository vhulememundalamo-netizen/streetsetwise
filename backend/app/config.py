from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"  # development | production
    database_url: str = "postgresql+psycopg://setwise_app:change-me@localhost:5432/setwise"

    # Secrets. In production these MUST come from a secret manager, never from git.
    jwt_secret: str = "dev-only-change-me-dev-only-change-me-32b"
    # Comma separated Fernet keys. First key encrypts, all keys can decrypt (key rotation).
    field_encryption_keys: str = ""
    # Used to hash lookup values (e.g. email) so they can be searched without storing plaintext.
    email_hash_pepper: str = "dev-only-pepper-change-me"

    access_token_minutes: int = 15
    refresh_token_days: int = 30
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    min_age_years: int = 18  # POPIA s35: children's data needs a competent person; we require 18+

    # AI coach. Off unless a key is set AND the user gave AI consent.
    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-5-5"
    ai_max_tokens: int = 500

    # Retention (POPIA s14): do not keep data longer than needed.
    inactive_account_days: int = 730
    audit_log_days: int = 365

    cors_origins: str = ""  # native apps do not need CORS; leave empty
    information_officer_email: str = "privacy@example.co.za"
    policy_version: str = "2026-10-15"

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_len(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return v

    @property
    def is_prod(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.is_prod:
        if s.jwt_secret.startswith("dev-only") or s.email_hash_pepper.startswith("dev-only"):
            raise RuntimeError("Refusing to start in production with development secrets")
        if not s.field_encryption_keys:
            raise RuntimeError("FIELD_ENCRYPTION_KEYS is required in production")
    return s
