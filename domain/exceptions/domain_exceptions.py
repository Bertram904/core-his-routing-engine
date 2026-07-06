"""Domain-level exception hierarchy for application error propagation."""

from typing import Final


class DomainError(Exception):
    """Base class for domain and application errors.

    Attributes:
        message: Human-readable error description.
    """

    def __init__(self, message: str) -> None:
        """Initialize the domain error.

        Args:
            message: Descriptive error message.
        """
        self._message: str = message
        super().__init__(message)

    @property
    def message(self) -> str:
        """Return the error message."""
        return self._message


class EntityNotFoundError(DomainError):
    """Raised when a requested domain entity cannot be located.

    Attributes:
        entity_name: Logical name of the missing entity type.
    """

    def __init__(self, entity_name: str, detail: str) -> None:
        """Initialize the not-found error.

        Args:
            entity_name: Entity type identifier (e.g., ``Workflow``).
            detail: Specific not-found description.
        """
        self._entity_name: str = entity_name
        super().__init__(detail)

    @property
    def entity_name(self) -> str:
        """Return the missing entity type name."""
        return self._entity_name


class AuthenticationError(DomainError):
    """Raised when user authentication or credential validation fails."""

    _DEFAULT_MESSAGE: Final[str] = "Invalid username or password"

    def __init__(self, message: str = _DEFAULT_MESSAGE) -> None:
        """Initialize the authentication error.

        Args:
            message: Authentication failure description.
        """
        super().__init__(message)
