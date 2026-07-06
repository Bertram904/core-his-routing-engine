"""Application-level field encryption with swappable algorithm strategies."""

from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import Text, TypeDecorator

from core.config import Settings, get_settings
from domain.interfaces import IEncryptionStrategy


class FernetEncryptionStrategy(IEncryptionStrategy):
    """Fernet-based symmetric encryption strategy.

    Uses AES-128-CBC with HMAC authentication via the ``cryptography`` library.

    Attributes:
        settings: Application settings supplying the encryption key.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the strategy with a validated Fernet key.

        Args:
            settings: Application settings containing the encryption key.

        Raises:
            ValueError: If the configured key is not Fernet-compatible.
        """
        self._settings: Settings = settings
        self._fernet: Fernet = self._build_fernet_cipher()

    @property
    def settings(self) -> Settings:
        """Return the bound application settings."""
        return self._settings

    def _build_fernet_cipher(self) -> Fernet:
        """Construct a Fernet cipher from the configured key.

        Returns:
            Initialized ``Fernet`` instance.

        Raises:
            ValueError: If the key format is invalid.
        """
        key = self._settings.encryption_key_value.encode("utf-8")
        try:
            return Fernet(key)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                "ENCRYPTION_KEY must be a valid Fernet url-safe "
                "base64-encoded 32-byte key."
            ) from exc

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using Fernet.

        Args:
            plaintext: Raw string to encrypt.

        Returns:
            URL-safe base64 ciphertext string.

        Raises:
            ValueError: If ``plaintext`` is empty.
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty plaintext.")
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a Fernet ciphertext token.

        Args:
            ciphertext: Stored encrypted token.

        Returns:
            Decrypted plaintext string.

        Raises:
            ValueError: If ``ciphertext`` is empty or tampered.
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty ciphertext.")
        try:
            plaintext_bytes = self._fernet.decrypt(ciphertext.encode("utf-8"))
        except InvalidToken as exc:
            raise ValueError("Ciphertext is invalid or has been tampered.") from exc
        return plaintext_bytes.decode("utf-8")


class EncryptionService:
    """Facade delegating encrypt/decrypt operations to a strategy.

    Consumers depend on this service rather than concrete algorithm classes,
    enabling runtime strategy substitution without changing call sites.

    Attributes:
        strategy: Active encryption strategy implementation.
    """

    def __init__(self, strategy: IEncryptionStrategy) -> None:
        """Bind an encryption strategy.

        Args:
            strategy: Strategy implementing ``IEncryptionStrategy``.
        """
        self._strategy: IEncryptionStrategy = strategy

    @property
    def strategy(self) -> IEncryptionStrategy:
        """Return the active encryption strategy."""
        return self._strategy

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext via the bound strategy.

        Args:
            plaintext: Raw sensitive value.

        Returns:
            Encrypted ciphertext suitable for persistence.
        """
        return self._strategy.encrypt(plaintext)

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext via the bound strategy.

        Args:
            ciphertext: Stored encrypted value.

        Returns:
            Original plaintext.
        """
        return self._strategy.decrypt(ciphertext)


class EncryptedString(TypeDecorator[str]):
    """SQLAlchemy column type that transparently encrypts string values at rest.

    Plaintext is encrypted on bind (write) and decrypted on load (read).
    The underlying database column stores ``Text`` ciphertext.

    Attributes:
        impl: SQLAlchemy storage type.
        cache_ok: Whether SQLAlchemy may cache compiled statements.
    """

    impl = Text
    cache_ok = True

    def __init__(
        self,
        encryption_service: EncryptionService | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize the type decorator.

        Args:
            encryption_service: Optional service override for testing.
            *args: Positional arguments forwarded to ``TypeDecorator``.
            **kwargs: Keyword arguments forwarded to ``TypeDecorator``.
        """
        super().__init__(*args, **kwargs)
        self._encryption_service: EncryptionService = (
            encryption_service or get_encryption_service()
        )

    @property
    def encryption_service(self) -> EncryptionService:
        """Return the bound encryption service."""
        return self._encryption_service

    def process_bind_param(
        self,
        value: str | None,
        dialect: Any,
    ) -> str | None:
        """Encrypt plaintext before persisting to the database.

        Args:
            value: Plaintext string from the ORM layer.
            dialect: Active SQLAlchemy dialect (unused).

        Returns:
            Encrypted ciphertext, or ``None`` if input is ``None``.
        """
        if value is None:
            return None
        return self._encryption_service.encrypt(value)

    def process_result_value(
        self,
        value: str | None,
        dialect: Any,
    ) -> str | None:
        """Decrypt ciphertext after loading from the database.

        Args:
            value: Stored ciphertext from the database.
            dialect: Active SQLAlchemy dialect (unused).

        Returns:
            Decrypted plaintext, or ``None`` if input is ``None``.
        """
        if value is None:
            return None
        return self._encryption_service.decrypt(value)


@lru_cache
def get_encryption_service() -> EncryptionService:
    """Return a cached ``EncryptionService`` singleton.

    Returns:
        Shared encryption service using the default Fernet strategy.
    """
    settings = get_settings()
    strategy = FernetEncryptionStrategy(settings)
    return EncryptionService(strategy)
