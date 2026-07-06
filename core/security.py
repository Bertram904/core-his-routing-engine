"""JWT token management and encapsulated password hashing."""

from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any, Final

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError

from core.async_executor import run_blocking_io
from core.config import Settings, get_settings
from core.constants import JwtClaim, TextEncoding
from domain.entities.token_payload import TokenPayload
from domain.interfaces import IPasswordHasher, ITokenService


class BcryptPasswordHasher(IPasswordHasher):
    """Bcrypt-based password hashing strategy.

    Uses the ``bcrypt`` adaptive hashing algorithm with an internal cost
    factor. Hashing logic is encapsulated and swappable via ``IPasswordHasher``.
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
        return self._hash_sync(plain_password)

    async def hash_password_async(self, plain_password: str) -> str:
        """Hash a password without blocking the async event loop.

        Args:
            plain_password: Raw password string.

        Returns:
            Bcrypt hash string.
        """
        return await run_blocking_io(lambda: self.hash_password(plain_password))

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
        return self._verify_sync(plain_password, hashed_password)

    async def verify_password_async(
        self,
        plain_password: str,
        hashed_password: str,
    ) -> bool:
        """Verify a password without blocking the async event loop.

        Args:
            plain_password: Raw password to verify.
            hashed_password: Stored bcrypt hash.

        Returns:
            ``True`` if credentials match, otherwise ``False``.
        """
        return await run_blocking_io(
            lambda: self.verify_password(plain_password, hashed_password)
        )

    def _hash_sync(self, plain_password: str) -> str:
        """Synchronously hash a password using bcrypt.

        Args:
            plain_password: Raw password string.

        Returns:
            Bcrypt hash string.
        """
        password_bytes = plain_password.encode(TextEncoding.UTF8)
        salt = bcrypt.gensalt(rounds=self._DEFAULT_ROUNDS)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode(TextEncoding.UTF8)

    def _verify_sync(self, plain_password: str, hashed_password: str) -> bool:
        """Synchronously verify a password against a bcrypt hash.

        Args:
            plain_password: Raw password to verify.
            hashed_password: Stored bcrypt hash.

        Returns:
            ``True`` if credentials match, otherwise ``False``.
        """
        return bcrypt.checkpw(
            plain_password.encode(TextEncoding.UTF8),
            hashed_password.encode(TextEncoding.UTF8),
        )


class JwtTokenService(ITokenService):
    """HS256 JWT token service with fine-grained scope embedding."""

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
            scopes: Permission scope strings.

        Returns:
            Encoded JWT access token.

        Raises:
            ValueError: If ``subject`` is empty.
        """
        if not subject:
            raise ValueError("JWT subject cannot be empty.")
        return self._encode_token(subject, scopes)

    async def create_access_token_async(self, subject: str, scopes: list[str]) -> str:
        """Create a JWT without blocking the async event loop.

        Args:
            subject: Unique user identifier.
            scopes: Permission scope strings.

        Returns:
            Encoded JWT access token.
        """
        return await run_blocking_io(
            lambda: self.create_access_token(subject, scopes)
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
        return self._decode_token(token)

    async def decode_access_token_async(self, token: str) -> TokenPayload:
        """Decode a JWT without blocking the async event loop.

        Args:
            token: Encoded JWT string.

        Returns:
            Parsed ``TokenPayload``.
        """
        return await run_blocking_io(lambda: self.decode_access_token(token))

    def _encode_token(self, subject: str, scopes: list[str]) -> str:
        """Build and sign a JWT payload.

        Args:
            subject: Principal identifier.
            scopes: Permission scopes.

        Returns:
            Encoded JWT string.
        """
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

    def _decode_token(self, token: str) -> TokenPayload:
        """Decode and validate a raw JWT string.

        Args:
            token: Encoded JWT string.

        Returns:
            Parsed ``TokenPayload``.

        Raises:
            ValueError: If the token is invalid or malformed.
        """
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
def get_password_hasher() -> IPasswordHasher:
    """Return a cached password hasher singleton.

    Returns:
        ``IPasswordHasher`` implementation.
    """
    return BcryptPasswordHasher(get_settings())


@lru_cache
def get_jwt_token_service() -> ITokenService:
    """Return a cached JWT token service singleton.

    Returns:
        ``ITokenService`` implementation.
    """
    return JwtTokenService(get_settings())
