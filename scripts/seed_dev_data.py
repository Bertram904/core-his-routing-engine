"""Seed development data for authentication and RBAC testing."""

import asyncio

from sqlalchemy import select

from core.security import get_password_hasher
from domain.models import (
    Patient,
    Permission,
    Role,
    RolePermission,
    RoutingRule,
    User,
    WorkflowStage,
)
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

        patient = Patient(name="Nguyen Van A")
        patient.identity_number = "001234567890"
        patient.phone = "0901234567"
        session.add(patient)

        session.add_all(
            [
                RoutingRule(
                    name="emergency_triage",
                    description="Route emergency department patients to triage",
                    source_stage=WorkflowStage.REGISTRATION,
                    target_stage=WorkflowStage.TRIAGE,
                    condition_expression='{"department": "emergency"}',
                    priority=0,
                    is_active=True,
                ),
                RoutingRule(
                    name="default_examination",
                    description="Default route to examination",
                    source_stage=WorkflowStage.REGISTRATION,
                    target_stage=WorkflowStage.EXAMINATION,
                    condition_expression="{}",
                    priority=10,
                    is_active=True,
                ),
            ]
        )

    await manager.dispose()
    print("Seed completed.")
    print("  username: dr_smith")
    print("  password: Secret123!")
    print("  scopes:   read:patient, write:clinical_record")
    print("  patient:  identity_number=001234567890, name=Nguyen Van A")
    print("  routing:  emergency -> triage, default -> examination")


if __name__ == "__main__":
    asyncio.run(seed())
