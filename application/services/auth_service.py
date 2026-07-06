"""Authentication use-case orchestration."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from application.dtos.auth_dto import TokenResponse, UserAuthProfile
from core.config import Settings
from core.constants import AuthErrorDetail, RedisKeyPrefix
from domain.interfaces import IPasswordHasher, ITokenService
from domain.models import Role, User
from infrastructure.cache.redis_client import RedisManager


class AuthService:
    """Orchestrates login, permission resolution, Redis caching, and JWT issuance.

    On login the service resolves user permissions via a joined DB query on
    cache miss, caches the profile in Redis, verifies credentials, and embeds
    fine-grained scopes in the JWT payload.

    Attributes:
        settings: Application configuration.
        password_hasher: Encapsulated password hashing strategy.
        token_service: JWT creation and validation service.
        redis_manager: Redis cache adapter.
    """

    _TOKEN_TYPE: str = "bearer"

    def __init__(
        self,
        settings: Settings,
        password_hasher: IPasswordHasher,
        token_service: ITokenService,
        redis_manager: RedisManager,
    ) -> None:
        """Wire authentication dependencies.

        Args:
            settings: Application settings.
            password_hasher: Password hashing strategy.
            token_service: JWT token service.
            redis_manager: Redis manager for permission caching.
        """
        self._settings: Settings = settings
        self._password_hasher: IPasswordHasher = password_hasher
        self._token_service: ITokenService = token_service
        self._redis_manager: RedisManager = redis_manager

    @property
    def settings(self) -> Settings:
        """Return the bound application settings."""
        return self._settings

    async def login(
        self,
        session: AsyncSession,
        username: str,
        password: str,
    ) -> TokenResponse:
        """Authenticate a user and return a scoped JWT access token.

        Args:
            session: Active async database session.
            username: Login identifier.
            password: Plaintext password.

        Returns:
            ``TokenResponse`` containing the signed JWT.

        Raises:
            HTTPException: 401 when credentials are invalid.
        """
        profile = await self._resolve_user_profile(session, username)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=AuthErrorDetail.INVALID_CREDENTIALS,
            )

        if not self._password_hasher.verify_password(
            password,
            profile.hashed_password,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=AuthErrorDetail.INVALID_CREDENTIALS,
            )

        access_token = self._token_service.create_access_token(
            subject=profile.username,
            scopes=profile.scopes,
        )
        expires_in = self._settings.jwt_expire_minutes * 60
        return TokenResponse(
            access_token=access_token,
            token_type=self._TOKEN_TYPE,
            expires_in=expires_in,
        )

    async def _resolve_user_profile(
        self,
        session: AsyncSession,
        username: str,
    ) -> UserAuthProfile | None:
        """Load a user auth profile from Redis cache or the database.

        Args:
            session: Active async database session.
            username: Login identifier.

        Returns:
            Resolved profile, or ``None`` when the user does not exist.
        """
        cache_key = self._build_cache_key(username)
        cached_value = await self._redis_manager.get(cache_key)
        if cached_value is not None:
            return UserAuthProfile.model_validate_json(cached_value)

        profile = await self._load_profile_from_database(session, username)
        if profile is None:
            return None

        await self._redis_manager.set(
            cache_key,
            profile.model_dump_json(),
            ttl_seconds=self._settings.auth_cache_ttl_seconds,
        )
        return profile

    async def _load_profile_from_database(
        self,
        session: AsyncSession,
        username: str,
    ) -> UserAuthProfile | None:
        """Query user with role and permissions using eager loading.

        Args:
            session: Active async database session.
            username: Login identifier.

        Returns:
            Built ``UserAuthProfile``, or ``None`` if not found.
        """
        statement = (
            select(User)
            .options(joinedload(User.role).joinedload(Role.permissions))
            .where(User.username == username)
        )
        result = await session.execute(statement)
        user = result.scalar_one_or_none()
        if user is None:
            return None

        scopes = sorted({permission.name for permission in user.role.permissions})
        return UserAuthProfile(
            user_id=user.id,
            username=user.username,
            role_name=user.role.name,
            hashed_password=user.hashed_password,
            scopes=scopes,
        )

    def _build_cache_key(self, username: str) -> str:
        """Build the Redis cache key for a username.

        Args:
            username: Login identifier.

        Returns:
            Namespaced Redis key string.
        """
        return f"{RedisKeyPrefix.USER_PERMISSIONS}:{username}"
