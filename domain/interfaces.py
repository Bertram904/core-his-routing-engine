"""Domain-layer contracts defining infrastructure and service boundaries."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from domain.constants import PaginationDefaults
from domain.entities.token_payload import TokenPayload

EntityT = TypeVar("EntityT")
IdentifierT = TypeVar("IdentifierT")


class IRepository(ABC, Generic[EntityT, IdentifierT]):
    """Contract for generic asynchronous CRUD persistence operations.

    Implementations must remain persistence-agnostic at the call site;
    consumers depend on this interface, not concrete storage adapters.

    Type Parameters:
        EntityT: Domain entity or ORM model type managed by the repository.
        IdentifierT: Primary-key type used to locate entities.
    """

    @abstractmethod
    async def get_by_id(self, entity_id: IdentifierT) -> EntityT | None:
        """Retrieve a single entity by its unique identifier.

        Args:
            entity_id: Primary key of the target entity.

        Returns:
            The matching entity, or ``None`` if not found.
        """

    @abstractmethod
    async def get_all(
        self,
        *,
        skip: int = PaginationDefaults.SKIP,
        limit: int = PaginationDefaults.LIMIT,
    ) -> list[EntityT]:
        """Retrieve a paginated collection of entities.

        Args:
            skip: Number of records to offset from the start.
            limit: Maximum number of records to return.

        Returns:
            Ordered list of entities within the requested page.
        """

    @abstractmethod
    async def create(self, entity: EntityT) -> EntityT:
        """Persist a new entity.

        Args:
            entity: Domain entity to insert.

        Returns:
            The persisted entity, potentially enriched with generated fields.
        """

    @abstractmethod
    async def update(self, entity: EntityT) -> EntityT:
        """Persist changes to an existing entity.

        Args:
            entity: Entity carrying updated state.

        Returns:
            The updated entity as stored.
        """

    @abstractmethod
    async def delete(self, entity_id: IdentifierT) -> bool:
        """Remove an entity by its identifier.

        Args:
            entity_id: Primary key of the entity to delete.

        Returns:
            ``True`` if a record was removed, ``False`` if not found.
        """

    @abstractmethod
    async def exists(self, entity_id: IdentifierT) -> bool:
        """Check whether an entity exists without loading it fully.

        Args:
            entity_id: Primary key to verify.

        Returns:
            ``True`` if the entity exists, otherwise ``False``.
        """


class IAsyncCacheClient(ABC):
    """Contract for asynchronous key-value cache adapters."""

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Retrieve a cached string value.

        Args:
            key: Cache key.

        Returns:
            Cached value or ``None`` when absent.
        """

    @abstractmethod
    async def set(self, key: str, value: str, *, ttl_seconds: int) -> None:
        """Store a string value with a TTL.

        Args:
            key: Cache key.
            value: String payload.
            ttl_seconds: Expiration in seconds.
        """


class IEncryptionStrategy(ABC):
    """Contract for symmetric application-level field encryption."""

    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string for persistence.

        Args:
            plaintext: Raw sensitive value.

        Returns:
            Encoded ciphertext safe for database storage.
        """

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a previously encrypted ciphertext.

        Args:
            ciphertext: Stored encrypted value.

        Returns:
            Original plaintext string.
        """


class IPasswordHasher(ABC):
    """Contract for one-way password hashing and verification."""

    @abstractmethod
    def hash_password(self, plain_password: str) -> str:
        """Hash a plaintext password for secure storage.

        Args:
            plain_password: Raw password supplied by the user.

        Returns:
            Encoded password hash string.
        """

    @abstractmethod
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a stored hash.

        Args:
            plain_password: Raw password to verify.
            hashed_password: Previously stored password hash.

        Returns:
            ``True`` if the password matches, otherwise ``False``.
        """


class ITokenService(ABC):
    """Contract for JWT access-token creation and validation."""

    @abstractmethod
    def create_access_token(self, subject: str, scopes: list[str]) -> str:
        """Create a signed JWT access token.

        Args:
            subject: Unique principal identifier (typically username).
            scopes: Fine-grained permission scopes embedded in the token.

        Returns:
            Encoded JWT string.
        """

    @abstractmethod
    def decode_access_token(self, token: str) -> TokenPayload:
        """Decode and validate a JWT access token.

        Args:
            token: Encoded JWT string from the Authorization header.

        Returns:
            Parsed ``TokenPayload`` object.

        Raises:
            ValueError: If the token is invalid or expired.
        """


class AbstractRuleEvaluator(ABC):
    """Contract for evaluating dynamic routing rule condition expressions.

    Concrete evaluators implement domain-specific matching logic. The
    ``DynamicRoutingEngine`` depends on this abstraction (polymorphism),
    not on any single parsing or matching strategy.
    """

    @abstractmethod
    def evaluate(self, condition_expression: str, context: dict[str, Any]) -> bool:
        """Determine whether a rule condition matches the supplied context.

        Args:
            condition_expression: Serialized rule condition (e.g., JSON DSL).
            context: Runtime facts used for rule matching.

        Returns:
            ``True`` when the rule condition is satisfied.
        """


class IPdfGenerator(ABC):
    """Contract for generating PDF documents from structured data."""

    @abstractmethod
    async def generate(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> bytes:
        """Render a PDF document from a named template and context data.

        Args:
            template_name: Logical template identifier (e.g., ``invoice``).
            context: Key-value pairs injected into the template engine.

        Returns:
            Raw PDF document bytes.

        Raises:
            NotImplementedError: When invoked on the abstract base itself.
            ValueError: When ``template_name`` or ``context`` is invalid.
        """

    @abstractmethod
    async def generate_from_html(self, html_content: str) -> bytes:
        """Render a PDF document directly from an HTML string.

        Args:
            html_content: Fully composed HTML markup.

        Returns:
            Raw PDF document bytes.

        Raises:
            ValueError: When ``html_content`` is empty or malformed.
        """
