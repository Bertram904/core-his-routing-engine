"""Seed development data for authentication and RBAC testing."""

import asyncio

from sqlalchemy import select

from core.security import get_password_hasher
from domain.models import (
    Patient,
    PatientWorkflow,
    Permission,
    Role,
    RolePermission,
    RoutingRule,
    User,
    WorkflowStage,
    WorkflowStatus,
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

        existing_user = await session.scalar(
            select(User).where(User.username == "dr_smith")
        )
        if existing_user is not None:
            print("Seed data already exists. Skipping.")
            await manager.dispose()
            return

        read_patient = Permission(
            name="read:patient",
            description="Read patient records",
        )
        write_clinical = Permission(
            name="write:clinical_record",
            description="Write clinical records",
        )
        permissions = [read_patient, write_clinical]
        session.add_all(permissions)
        await session.flush()

        physician_role = Role(name="physician")
        reception_role = Role(name="reception_clerk")
        session.add_all([physician_role, reception_role])
        await session.flush()

        for permission in permissions:
            session.add(
                RolePermission(
                    role_id=physician_role.id,
                    permission_id=permission.id,
                )
            )

        session.add(
            RolePermission(
                role_id=reception_role.id,
                permission_id=read_patient.id,
            )
        )

        physician = User(username="dr_smith", role_id=physician_role.id)
        physician.set_hashed_password(password_hasher.hash_password("Secret123!"))
        reception_clerk = User(username="recep_clerk", role_id=reception_role.id)
        reception_clerk.set_hashed_password(
            password_hasher.hash_password("Secret123!")
        )
        session.add_all([physician, reception_clerk])

        patient = Patient(name="Nguyen Van A")
        patient.identity_number = "001234567890"
        patient.phone = "0901234567"
        session.add(patient)
        await session.flush()

        session.add(
            PatientWorkflow(
                patient_id=patient.id,
                current_stage=WorkflowStage.REGISTRATION,
                status=WorkflowStatus.IN_PROGRESS,
                assigned_department="reception",
            )
        )

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
    print("  physician:  dr_smith / Secret123!")
    print("  reception:  recep_clerk / Secret123!")
    print("  scopes:")
    print("    dr_smith    -> read:patient, write:clinical_record")
    print("    recep_clerk -> read:patient")
    print("  patient:  identity_number=001234567890, name=Nguyen Van A")
    print("  routing:  emergency -> triage, default -> examination")


if __name__ == "__main__":
    asyncio.run(seed())
