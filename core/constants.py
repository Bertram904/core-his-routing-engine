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


class JwtDefaults:
    """Default JWT signing configuration."""

    ALGORITHM: Final[str] = "HS256"
    EXPIRE_MINUTES: Final[int] = 30


class AuthCacheDefaults:
    """Default TTL for cached authentication mappings."""

    TTL_SECONDS: Final[int] = 3600


class JwtClaim:
    """Registered and custom JWT claim names."""

    SUBJECT: Final[str] = "sub"
    SCOPES: Final[str] = "scopes"
    EXPIRATION: Final[str] = "exp"
    ISSUED_AT: Final[str] = "iat"


class AuthErrorDetail:
    """Standardized authentication and authorization error messages."""

    NOT_ENOUGH_PERMISSIONS: Final[str] = "Not enough permissions"
    INVALID_CREDENTIALS: Final[str] = "Invalid username or password"
    INVALID_TOKEN: Final[str] = "Invalid or expired token"
    MISSING_TOKEN: Final[str] = "Authentication credentials were not provided"


class RedisKeyPrefix:
    """Redis key namespaces for infrastructure adapters."""

    USER_PERMISSIONS: Final[str] = "user_permissions"
    ROUTING_RULES: Final[str] = "routing_rules"


class RoutingCacheDefaults:
    """Default TTL for cached routing rule sets."""

    TTL_SECONDS: Final[int] = 1800


class PdfDefaults:
    """PDF generation defaults."""

    MEDIA_TYPE: Final[str] = "application/pdf"
    CLINICAL_WORKFLOW_TEMPLATE: Final[str] = "clinical_workflow"
    TEMPLATE_EXTENSION: Final[str] = ".html"


class ClinicalErrorDetail:
    """Clinical workflow error messages."""

    WORKFLOW_NOT_FOUND: Final[str] = "Workflow not found"
    AUTHOR_NOT_FOUND: Final[str] = "Author user not found"
