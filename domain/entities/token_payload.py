"""Immutable domain value objects."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenPayload:
    """Decoded JWT access-token payload.

    Attributes:
        subject: Principal identifier (``sub`` claim).
        scopes: Fine-grained permission scopes granted to the principal.
    """

    subject: str
    scopes: tuple[str, ...]
