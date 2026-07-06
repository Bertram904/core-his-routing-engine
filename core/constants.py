"""Application-wide constants for configuration and infrastructure wiring."""

from typing import Final


class ConfigFile:
    """Filesystem paths and encodings for configuration loading."""

    ENV_FILE: Final[str] = ".env"
    ENV_ENCODING: Final[str] = "utf-8"


class DatabaseDriver:
    """Database connection driver identifiers."""

    ASYNC_POSTGRES: Final[str] = "postgresql+asyncpg"


class RedisScheme:
    """Redis URL scheme prefix."""

    DEFAULT: Final[str] = "redis"


class UrlMask:
    """Redaction tokens for log-safe URL rendering."""

    CREDENTIAL: Final[str] = "***"


class TextEncoding:
    """Standard text encodings used across cryptographic adapters."""

    UTF8: Final[str] = "utf-8"
