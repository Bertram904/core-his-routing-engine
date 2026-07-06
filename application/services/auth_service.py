"""Authentication use-case orchestration."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from application.dtos.auth_dto import TokenResponse, UserAuthProfile
from core.async_executor import run_blocking_io
from core.config import Settings
from core.constants import AuthErrorDetail, RedisKeyPrefix
from domain.exceptions.domain_exceptions import AuthenticationError
from domain.interfaces import IAsyncCacheClient, IPasswordHasher, ITokenService
from domain.models import Role, User


class AuthService:
    """Orchestrates login, permission resolution, Redis caching, and JWT issuance."""

    _TOKEN_TYPE: str = "bearer"

    def __init__(
        self,
        settings: Settings,
        password_hasher: IPasswordHasher,
        token_service: ITokenService,
        cache_client: IAsyncCacheClient,
    ) -> None:
        """Wire authentication dependencies.

        Args:
            settings: Application settings.
            password_hasher: Password hashing strategy.
            token_service: JWT token service.
            cache_client: Async cache adapter.
        """
        self._settings: Settings = settings
        self._password_hasher: IPasswordHasher = password_hasher
        self._token_service: ITokenService = token_service
        self._cache_client: IAsyncCacheClient = cache_client

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
            AuthenticationError: When credentials are invalid.
        """
        profile = await self._resolve_user_profile(session, username)
        await self._validate_credentials(password, profile)
        return await self._build_token_response(profile)

    async def _validate_credentials(
        self,
        password: str,
        profile: UserAuthProfile | None,
    ) -> None:
        """Verify that the profile exists and the password matches.

        Args:
            password: Plaintext password.
            profile: Resolved user profile.

        Raises:
            AuthenticationError: When credentials are invalid.
        """
        if profile is None:
            raise AuthenticationError(AuthErrorDetail.INVALID_CREDENTIALS)

        is_valid = await run_blocking_io(
            lambda: self._password_hasher.verify_password(
                password,
                profile.hashed_password,
            )
        )
        if not is_valid:
            raise AuthenticationError(AuthErrorDetail.INVALID_CREDENTIALS)

    async def _build_token_response(self, profile: UserAuthProfile) -> TokenResponse:
        """Create a token response for an authenticated profile.

        Args:
            profile: Authenticated user profile.

        Returns:
            ``TokenResponse`` with a signed JWT.
        """
        access_token = await run_blocking_io(
            lambda: self._token_service.create_access_token(
                subject=profile.username,
                scopes=profile.scopes,
            )
        )
        return TokenResponse(
            access_token=access_token,
            token_type=self._TOKEN_TYPE,
            expires_in=self._settings.jwt_expire_minutes * 60,
        )

    async def _resolve_user_profile(
        self,
        session: AsyncSession,
        username: str,
    ) -> UserAuthProfile | None:
        """Load a user auth profile from cache or the database.

        Args:
            session: Active async database session.
            username: Login identifier.

        Returns:
            Resolved profile, or ``None`` when the user does not exist.
        """
        cache_key = self._build_cache_key(username)
        cached_value = await self._cache_client.get(cache_key)
        if cached_value is not None:
            return UserAuthProfile.model_validate_json(cached_value)

        profile = await self._load_profile_from_database(session, username)
        if profile is None:
            return None

        await self._cache_client.set(
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
            .options(
                selectinload(User.role).selectinload(Role.permissions),
            )
            .where(User.username == username)
        )
        result = await session.execute(statement)
        user = result.scalar_one_or_none()
        if user is None:
            return None

        return self._map_user_to_profile(user)

    def _map_user_to_profile(self, user: User) -> UserAuthProfile:
        """Map an ORM user graph to an auth profile DTO.

        Args:
            user: User with eagerly loaded role and permissions.

        Returns:
            ``UserAuthProfile`` ready for caching and JWT issuance.
        """
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
