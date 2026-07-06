"""Authentication data transfer objects."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credentials submitted to the login endpoint.

    Attributes:
        username: Unique user login identifier.
        password: Raw plaintext password.
    """

    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """JWT access-token response returned after successful authentication.

    Attributes:
        access_token: Signed JWT embedding fine-grained scopes.
        token_type: OAuth2 token type identifier.
        expires_in: Token lifetime in seconds.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserAuthProfile(BaseModel):
    """Cached user authentication profile with permission scopes.

    Attributes:
        user_id: Internal user primary key.
        username: Login identifier used as JWT subject.
        role_name: Assigned role name for diagnostics.
        hashed_password: Bcrypt hash used for credential verification.
        scopes: Fine-grained permission scope strings.
    """

    user_id: int
    username: str
    role_name: str
    hashed_password: str
    scopes: list[str]
