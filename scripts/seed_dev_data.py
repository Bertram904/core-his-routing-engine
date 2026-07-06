"""Seed development data for authentication and RBAC testing."""

import asyncio

from sqlalchemy import select

from core.security import get_password_hasher
from domain.models import Permission, Role, RolePermission, User
from infrastructure.database import Base, get_database_manager
import domain.models  # noqa: F401 — register ORM models with metadata


async def seed() -> None:
    """Create tables and seed a demo user with fine-grained permissions."""
    manager = get_database_manager()
    manager.connect()
    password_hasher = get_password_hasher()

    async with manager.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with manager.session_scope() as session:
        existing_user = await session.scalar(
            select(User).where(User.username == "dr_smith")
        )
        if existing_user is not None:
            print("Seed data already exists. Skipping.")
            await manager.dispose()
            return

        permissions = [
            Permission(name="read:patient", description="Read patient records"),
            Permission(
                name="write:clinical_record",
                description="Write clinical records",
            ),
        ]
        session.add_all(permissions)
        await session.flush()

        role = Role(name="physician")
        session.add(role)
        await session.flush()

        for permission in permissions:
            session.add(
                RolePermission(role_id=role.id, permission_id=permission.id)
            )

        user = User(username="dr_smith", role_id=role.id)
        user.set_hashed_password(password_hasher.hash_password("Secret123!"))
        session.add(user)

    await manager.dispose()
    print("Seed completed.")
    print("  username: dr_smith")
    print("  password: Secret123!")
    print("  scopes:   read:patient, write:clinical_record")


if __name__ == "__main__":
    asyncio.run(seed())
