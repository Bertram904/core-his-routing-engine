"""JWT token management and encapsulated password hashing."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any, Final

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError

from core.config import Settings, get_settings
from core.constants import JwtClaim, TextEncoding
from domain.interfaces import IPasswordHasher, ITokenService


class BcryptPasswordHasher(IPasswordHasher):
    """Bcrypt-based password hashing strategy.

    Uses the ``bcrypt`` adaptive hashing algorithm with an internal cost
    factor. Hashing logic is encapsulated and swappable via ``IPasswordHasher``.

    Attributes:
        settings: Application settings (reserved for future cost-factor config).
    """

    _DEFAULT_ROUNDS: Final[int] = 12

    def __init__(self, settings: Settings) -> None:
        """Initialize the hasher.

        Args:
            settings: Application settings instance.
        """
        self._settings: Settings = settings

    @property
    def settings(self) -> Settings:
        """Return the bound application settings."""
        return self._settings

    def hash_password(self, plain_password: str) -> str:
        """Hash a plaintext password using bcrypt.

        Args:
            plain_password: Raw password string.

        Returns:
            Bcrypt hash as a UTF-8 decoded string.

        Raises:
            ValueError: If ``plain_password`` is empty.
        """
        if not plain_password:
            raise ValueError("Cannot hash an empty password.")
        password_bytes = plain_password.encode(TextEncoding.UTF8)
        salt = bcrypt.gensalt(rounds=self._DEFAULT_ROUNDS)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode(TextEncoding.UTF8)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a bcrypt hash.

        Args:
            plain_password: Raw password to verify.
            hashed_password: Stored bcrypt hash.

        Returns:
            ``True`` if credentials match, otherwise ``False``.
        """
        if not plain_password or not hashed_password:
            return False
        return bcrypt.checkpw(
            plain_password.encode(TextEncoding.UTF8),
            hashed_password.encode(TextEncoding.UTF8),
        )


@dataclass(frozen=True)
class TokenPayload:
    """Immutable decoded JWT access-token payload.

    Attributes:
        subject: Principal identifier (``sub`` claim).
        scopes: Fine-grained permission scopes granted to the principal.
    """

    subject: str
    scopes: tuple[str, ...]


class JwtTokenService(ITokenService):
    """HS256 JWT token service with fine-grained scope embedding.

    Token payload format::

        {"sub": "user123", "scopes": ["read:patient", "write:clinical_record"]}

    Attributes:
        settings: Application settings supplying signing parameters.
    """

    def __init__(self, settings: Settings) -> None:
        """Bind signing configuration.

        Args:
            settings: Validated application settings.
        """
        self._settings: Settings = settings

    @property
    def settings(self) -> Settings:
        """Return the bound application settings."""
        return self._settings

    def create_access_token(self, subject: str, scopes: list[str]) -> str:
        """Create a signed JWT embedding permission scopes.

        Args:
            subject: Unique user identifier stored in the ``sub`` claim.
            scopes: Permission scope strings (e.g., ``write:clinical_record``).

        Returns:
            Encoded JWT access token.

        Raises:
            ValueError: If ``subject`` is empty.
        """
        if not subject:
            raise ValueError("JWT subject cannot be empty.")

        now = datetime.now(UTC)
        expire_at = now + timedelta(minutes=self._settings.jwt_expire_minutes)
        payload: dict[str, Any] = {
            JwtClaim.SUBJECT: subject,
            JwtClaim.SCOPES: sorted(set(scopes)),
            JwtClaim.ISSUED_AT: now,
            JwtClaim.EXPIRATION: expire_at,
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret_key_value,
            algorithm=self._settings.jwt_algorithm,
        )

    def decode_access_token(self, token: str) -> TokenPayload:
        """Decode and validate a JWT, returning a ``TokenPayload``.

        Args:
            token: Encoded JWT string.

        Returns:
            Parsed ``TokenPayload`` with subject and scopes.

        Raises:
            ValueError: If the token is missing, invalid, or expired.
        """
        if not token:
            raise ValueError("Token cannot be empty.")

        try:
            raw_payload = jwt.decode(
                token,
                self._settings.jwt_secret_key_value,
                algorithms=[self._settings.jwt_algorithm],
            )
        except InvalidTokenError as exc:
            raise ValueError("Invalid or expired token.") from exc

        subject = raw_payload.get(JwtClaim.SUBJECT)
        if not subject or not isinstance(subject, str):
            raise ValueError("Token is missing a valid subject claim.")

        raw_scopes = raw_payload.get(JwtClaim.SCOPES, [])
        if not isinstance(raw_scopes, list):
            raise ValueError("Token scopes claim must be a list.")

        scopes = tuple(str(scope) for scope in raw_scopes)
        return TokenPayload(subject=subject, scopes=scopes)


@lru_cache
def get_password_hasher() -> BcryptPasswordHasher:
    """Return a cached ``BcryptPasswordHasher`` singleton.

    Returns:
        Shared password hasher instance.
    """
    return BcryptPasswordHasher(get_settings())


@lru_cache
def get_jwt_token_service() -> JwtTokenService:
    """Return a cached ``JwtTokenService`` singleton.

    Returns:
        Shared JWT token service instance.
    """
    return JwtTokenService(get_settings())
