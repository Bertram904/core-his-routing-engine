"""Application configuration loaded securely from environment variables."""

from enum import Enum
from functools import lru_cache
from typing import Final

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.constants import (
    AuthCacheDefaults,
    ConfigFile,
    DatabaseDriver,
    JwtDefaults,
    RedisScheme,
    UrlMask,
)


class Environment(str, Enum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    """Encapsulated application settings with validated environment bindings.

    Sensitive values are stored as ``SecretStr`` and exposed only through
    read-only properties. Internal state is never mutated after initialization.

    Attributes:
        app_name: Human-readable application identifier.
        app_version: Semantic version string.
        environment: Current deployment environment.
        debug: Whether debug mode is enabled.
        api_prefix: URL prefix for all API routes.
        postgres_host: PostgreSQL host address.
        postgres_port: PostgreSQL port number.
        postgres_user: PostgreSQL username.
        postgres_password: PostgreSQL password (secret).
        postgres_db: PostgreSQL database name.
        redis_host: Redis host address.
        redis_port: Redis port number.
        redis_password: Redis password (secret, optional).
        redis_db: Redis logical database index.
        db_pool_size: SQLAlchemy connection pool size.
        db_max_overflow: Maximum overflow connections beyond pool size.
        db_pool_timeout_seconds: Seconds to wait for a pooled connection.
        db_echo: Whether SQLAlchemy should log SQL statements.
    """

    model_config = SettingsConfigDict(
        env_file=ConfigFile.ENV_FILE,
        env_file_encoding=ConfigFile.ENV_ENCODING,
        case_sensitive=False,
        extra="ignore",
    )

    _DEFAULT_POOL_SIZE: Final[int] = 10
    _DEFAULT_MAX_OVERFLOW: Final[int] = 20
    _DEFAULT_POOL_TIMEOUT_SECONDS: Final[int] = 30
    _DEFAULT_POSTGRES_PORT: Final[int] = 5432
    _DEFAULT_REDIS_PORT: Final[int] = 6379
    _DEFAULT_REDIS_DB: Final[int] = 0

    app_name: str = Field(default="Core HIS", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        alias="ENVIRONMENT",
    )
    debug: bool = Field(default=False, alias="DEBUG")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")

    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(
        default=_DEFAULT_POSTGRES_PORT,
        alias="POSTGRES_PORT",
    )
    postgres_user: str = Field(default="his_user", alias="POSTGRES_USER")
    postgres_password: SecretStr = Field(
        default=SecretStr("his_password"),
        alias="POSTGRES_PASSWORD",
    )
    postgres_db: str = Field(default="his_db", alias="POSTGRES_DB")

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=_DEFAULT_REDIS_PORT, alias="REDIS_PORT")
    redis_password: SecretStr | None = Field(
        default=None,
        alias="REDIS_PASSWORD",
    )
    redis_db: int = Field(default=_DEFAULT_REDIS_DB, alias="REDIS_DB")

    db_pool_size: int = Field(
        default=_DEFAULT_POOL_SIZE,
        alias="DB_POOL_SIZE",
    )
    db_max_overflow: int = Field(
        default=_DEFAULT_MAX_OVERFLOW,
        alias="DB_MAX_OVERFLOW",
    )
    db_pool_timeout_seconds: int = Field(
        default=_DEFAULT_POOL_TIMEOUT_SECONDS,
        alias="DB_POOL_TIMEOUT_SECONDS",
    )
    db_echo: bool = Field(default=False, alias="DB_ECHO")

    encryption_key: SecretStr = Field(
        default=SecretStr("MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="),
        alias="ENCRYPTION_KEY",
    )

    jwt_secret_key: SecretStr = Field(
        default=SecretStr("change-me-in-production-jwt-secret-key"),
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(
        default=JwtDefaults.ALGORITHM,
        alias="JWT_ALGORITHM",
    )
    jwt_expire_minutes: int = Field(
        default=JwtDefaults.EXPIRE_MINUTES,
        alias="JWT_EXPIRE_MINUTES",
    )
    auth_cache_ttl_seconds: int = Field(
        default=AuthCacheDefaults.TTL_SECONDS,
        alias="AUTH_CACHE_TTL_SECONDS",
    )

    @field_validator("environment", mode="before")
    @classmethod
    def _normalize_environment(cls, value: str | Environment) -> Environment:
        """Normalize environment input to a valid ``Environment`` enum member.

        Args:
            value: Raw environment string or enum value.

        Returns:
            Resolved ``Environment`` enum member.

        Raises:
            ValueError: If the provided value is not a recognized environment.
        """
        if isinstance(value, Environment):
            return value
        normalized = str(value).strip().lower()
        try:
            return Environment(normalized)
        except ValueError as exc:
            allowed = ", ".join(member.value for member in Environment)
            raise ValueError(
                f"Invalid environment '{value}'. Allowed: {allowed}."
            ) from exc

    @property
    def is_production(self) -> bool:
        """Return whether the application runs in production."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_debug_enabled(self) -> bool:
        """Return whether debug mode is active (never in production)."""
        if self.is_production:
            return False
        return self.debug

    @property
    def database_url(self) -> str:
        """Build the async PostgreSQL connection URL.

        Returns:
            SQLAlchemy-compatible async PostgreSQL DSN.
        """
        password = self.postgres_password.get_secret_value()
        return (
            f"{DatabaseDriver.ASYNC_POSTGRES}://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Build the Redis connection URL.

        Returns:
            Redis DSN with optional authentication.
        """
        if self.redis_password is not None:
            password = self.redis_password.get_secret_value()
            return (
                f"{RedisScheme.DEFAULT}://:{password}@{self.redis_host}:"
                f"{self.redis_port}/{self.redis_db}"
            )
        return (
            f"{RedisScheme.DEFAULT}://{self.redis_host}:"
            f"{self.redis_port}/{self.redis_db}"
        )

    @property
    def encryption_key_value(self) -> str:
        """Return the raw encryption key for cryptographic adapters.

        Returns:
            Decoded encryption key string.
        """
        return self.encryption_key.get_secret_value()

    @property
    def jwt_secret_key_value(self) -> str:
        """Return the raw JWT signing secret.

        Returns:
            Decoded JWT secret string.
        """
        return self.jwt_secret_key.get_secret_value()

    def masked_database_url(self) -> str:
        """Return a log-safe database URL with credentials redacted.

        Returns:
            Database DSN suitable for logging and diagnostics.
        """
        return (
            f"{DatabaseDriver.ASYNC_POSTGRES}://{self.postgres_user}:"
            f"{UrlMask.CREDENTIAL}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached, immutable ``Settings`` singleton.

    Returns:
        Validated application settings loaded once per process.
    """
    return Settings()
