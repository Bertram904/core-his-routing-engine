"""SQLAlchemy 2.0 declarative ORM models for the Core HIS domain."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from domain.constants import (
    ColumnLength,
    ForeignKeyAction,
    RoutingRuleDefaults,
    TableName,
    foreign_key_reference,
)
from infrastructure.database import Base
from infrastructure.security.encryption import EncryptedString

def _enum_values(enum_class: type[Enum]) -> list[str]:
    """Extract string values from a string-backed enum class.

    Args:
        enum_class: Enum class with string values.

    Returns:
        List of enum member values for SQLAlchemy storage.
    """
    return [member.value for member in enum_class]


class WorkflowStage(str, Enum):
    """Ordered stages in a patient care workflow."""

    REGISTRATION = "registration"
    TRIAGE = "triage"
    EXAMINATION = "examination"
    DIAGNOSTICS = "diagnostics"
    TREATMENT = "treatment"
    DISCHARGE = "discharge"


class WorkflowStatus(str, Enum):
    """Lifecycle status of a patient workflow instance."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ClinicalRecordStatus(str, Enum):
    """Publication status of a clinical record."""

    DRAFT = "draft"
    FINALIZED = "finalized"
    ARCHIVED = "archived"


class Permission(Base):
    """Fine-grained permission atom for RBAC authorization checks.

    Attributes:
        id: Primary key.
        name: Machine-readable permission identifier (e.g., ``write:clinical_record``).
        description: Human-readable explanation of the permission scope.
    """

    __tablename__ = TableName.PERMISSIONS

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(ColumnLength.PERMISSION_NAME),
        unique=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(ColumnLength.DESCRIPTION),
        nullable=True,
    )

    roles: Mapped[list[Role]] = relationship(
        secondary=TableName.ROLE_PERMISSIONS,
        back_populates="permissions",
    )

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name!r})>"


class Role(Base):
    """Role aggregate grouping multiple permissions for assignment to users.

    Attributes:
        id: Primary key.
        name: Unique role identifier (e.g., ``physician``, ``nurse``).
    """

    __tablename__ = TableName.ROLES

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(ColumnLength.ROLE_NAME),
        unique=True,
        index=True,
    )

    permissions: Mapped[list[Permission]] = relationship(
        secondary=TableName.ROLE_PERMISSIONS,
        back_populates="roles",
    )
    users: Mapped[list[User]] = relationship(back_populates="role")
    role_permission_links: Mapped[list[RolePermission]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name!r})>"


class RolePermission(Base):
    """Association entity linking roles to permissions (many-to-many).

    Attributes:
        role_id: Foreign key to the parent role.
        permission_id: Foreign key to the granted permission.
        granted_at: Timestamp when the permission was associated.
    """

    __tablename__ = TableName.ROLE_PERMISSIONS

    role_id: Mapped[int] = mapped_column(
        ForeignKey(
            foreign_key_reference(TableName.ROLES),
            ondelete=ForeignKeyAction.CASCADE,
        ),
        primary_key=True,
    )
    permission_id: Mapped[int] = mapped_column(
        ForeignKey(
            foreign_key_reference(TableName.PERMISSIONS),
            ondelete=ForeignKeyAction.CASCADE,
        ),
        primary_key=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    role: Mapped[Role] = relationship(back_populates="role_permission_links")
    permission: Mapped[Permission] = relationship()

    def __repr__(self) -> str:
        return (
            f"<RolePermission(role_id={self.role_id}, "
            f"permission_id={self.permission_id})>"
        )


class User(Base):
    """Authenticated system user bound to a single role.

    Sensitive credential data is encapsulated; the hashed password is never
    exposed in string representations.

    Attributes:
        id: Primary key.
        username: Unique login identifier.
        role_id: Foreign key to the assigned role.
    """

    __tablename__ = TableName.USERS

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(ColumnLength.USERNAME),
        unique=True,
        index=True,
    )
    _hashed_password: Mapped[str] = mapped_column(
        "hashed_password",
        String(ColumnLength.PASSWORD_HASH),
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey(
            foreign_key_reference(TableName.ROLES),
            ondelete=ForeignKeyAction.RESTRICT,
        ),
        index=True,
    )

    role: Mapped[Role] = relationship(back_populates="users")
    clinical_records: Mapped[list[ClinicalRecord]] = relationship(
        back_populates="author",
    )

    @property
    def hashed_password(self) -> str:
        """Return the stored password hash (read-only accessor)."""
        return self._hashed_password

    def set_hashed_password(self, hashed_value: str) -> None:
        """Assign a pre-hashed password value.

        Args:
            hashed_value: Bcrypt or Argon2 hash string.

        Raises:
            ValueError: If the provided hash is empty.
        """
        if not hashed_value:
            raise ValueError("Hashed password cannot be empty.")
        self._hashed_password = hashed_value

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username!r})>"


class Patient(Base):
    """Patient demographic record with encrypted PII fields.

    ``identity_number`` and ``phone`` are encrypted at rest via ``EncryptedString``
    and accessed exclusively through encapsulated property accessors.

    Attributes:
        id: Primary key.
        name: Patient full name (non-sensitive).
    """

    __tablename__ = TableName.PATIENTS

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(ColumnLength.ENTITY_NAME), index=True)
    _identity_number: Mapped[str | None] = mapped_column(
        "identity_number",
        EncryptedString(),
        nullable=True,
    )
    _phone: Mapped[str | None] = mapped_column(
        "phone",
        EncryptedString(),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    workflows: Mapped[list[PatientWorkflow]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    clinical_records: Mapped[list[ClinicalRecord]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
    )

    @property
    def identity_number(self) -> str | None:
        """Return the decrypted national identity number."""
        return self._identity_number

    @identity_number.setter
    def identity_number(self, value: str | None) -> None:
        """Set the national identity number (encrypted on persist)."""
        self._identity_number = value

    @property
    def phone(self) -> str | None:
        """Return the decrypted phone number."""
        return self._phone

    @phone.setter
    def phone(self, value: str | None) -> None:
        """Set the phone number (encrypted on persist)."""
        self._phone = value

    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, name={self.name!r})>"


class RoutingRule(Base):
    """Rule engine definition for routing patients between workflow stages.

    Attributes:
        id: Primary key.
        name: Unique rule identifier.
        description: Optional human-readable summary.
        source_stage: Workflow stage that triggers evaluation.
        target_stage: Destination stage when the rule matches.
        condition_expression: JSON or DSL expression evaluated at runtime.
        priority: Lower values are evaluated first.
        is_active: Whether the rule participates in routing decisions.
    """

    __tablename__ = TableName.ROUTING_RULES

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(ColumnLength.ENTITY_NAME),
        unique=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(ColumnLength.DESCRIPTION),
        nullable=True,
    )
    source_stage: Mapped[WorkflowStage] = mapped_column(
        SAEnum(
            WorkflowStage,
            values_callable=_enum_values,
            native_enum=False,
            length=ColumnLength.ENTITY_NAME,
        ),
        index=True,
    )
    target_stage: Mapped[WorkflowStage] = mapped_column(
        SAEnum(
            WorkflowStage,
            values_callable=_enum_values,
            native_enum=False,
            length=ColumnLength.ENTITY_NAME,
        ),
        index=True,
    )
    condition_expression: Mapped[str] = mapped_column(
        String(ColumnLength.CONDITION_EXPRESSION),
    )
    priority: Mapped[int] = mapped_column(
        default=RoutingRuleDefaults.PRIORITY,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        default=RoutingRuleDefaults.IS_ACTIVE,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    workflows: Mapped[list[PatientWorkflow]] = relationship(
        back_populates="routing_rule",
    )

    def __repr__(self) -> str:
        return (
            f"<RoutingRule(id={self.id}, name={self.name!r}, "
            f"source={self.source_stage!r}, target={self.target_stage!r})>"
        )


class PatientWorkflow(Base):
    """Active workflow instance tracking a patient through care stages.

    Attributes:
        id: Primary key.
        patient_id: Foreign key to the patient.
        routing_rule_id: Optional FK to the rule that advanced this workflow.
        current_stage: Present workflow stage.
        status: Workflow lifecycle status.
        assigned_department: Department currently responsible.
        notes: Free-text operational notes.
        started_at: Workflow initiation timestamp.
        completed_at: Workflow completion timestamp (``None`` if ongoing).
    """

    __tablename__ = TableName.PATIENT_WORKFLOWS

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey(
            foreign_key_reference(TableName.PATIENTS),
            ondelete=ForeignKeyAction.CASCADE,
        ),
        index=True,
    )
    routing_rule_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            foreign_key_reference(TableName.ROUTING_RULES),
            ondelete=ForeignKeyAction.SET_NULL,
        ),
        nullable=True,
        index=True,
    )
    current_stage: Mapped[WorkflowStage] = mapped_column(
        SAEnum(
            WorkflowStage,
            values_callable=_enum_values,
            native_enum=False,
            length=ColumnLength.ENTITY_NAME,
        ),
        index=True,
    )
    status: Mapped[WorkflowStatus] = mapped_column(
        SAEnum(
            WorkflowStatus,
            values_callable=_enum_values,
            native_enum=False,
            length=ColumnLength.ENTITY_NAME,
        ),
        default=WorkflowStatus.PENDING,
        index=True,
    )
    assigned_department: Mapped[str | None] = mapped_column(
        String(ColumnLength.DEPARTMENT),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    patient: Mapped[Patient] = relationship(back_populates="workflows")
    routing_rule: Mapped[RoutingRule | None] = relationship(
        back_populates="workflows",
    )

    def __repr__(self) -> str:
        return (
            f"<PatientWorkflow(id={self.id}, patient_id={self.patient_id}, "
            f"stage={self.current_stage!r}, status={self.status!r})>"
        )


class ClinicalRecord(Base):
    """Clinical documentation authored by a healthcare user for a patient.

    Attributes:
        id: Primary key.
        patient_id: Foreign key to the subject patient.
        author_id: Foreign key to the authoring user.
        record_type: Category of clinical content (e.g., ``diagnosis``).
        title: Short record heading.
        content: Full clinical narrative body.
        status: Publication lifecycle status.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
    """

    __tablename__ = TableName.CLINICAL_RECORDS

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey(
            foreign_key_reference(TableName.PATIENTS),
            ondelete=ForeignKeyAction.CASCADE,
        ),
        index=True,
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey(
            foreign_key_reference(TableName.USERS),
            ondelete=ForeignKeyAction.RESTRICT,
        ),
        index=True,
    )
    record_type: Mapped[str] = mapped_column(
        String(ColumnLength.RECORD_TYPE),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(ColumnLength.TITLE))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[ClinicalRecordStatus] = mapped_column(
        SAEnum(
            ClinicalRecordStatus,
            values_callable=_enum_values,
            native_enum=False,
            length=ColumnLength.ENTITY_NAME,
        ),
        default=ClinicalRecordStatus.DRAFT,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    patient: Mapped[Patient] = relationship(back_populates="clinical_records")
    author: Mapped[User] = relationship(back_populates="clinical_records")

    def __repr__(self) -> str:
        return (
            f"<ClinicalRecord(id={self.id}, patient_id={self.patient_id}, "
            f"title={self.title!r}, status={self.status!r})>"
        )


__all__ = [
    "ClinicalRecord",
    "ClinicalRecordStatus",
    "Patient",
    "PatientWorkflow",
    "Permission",
    "Role",
    "RolePermission",
    "RoutingRule",
    "User",
    "WorkflowStage",
    "WorkflowStatus",
]
