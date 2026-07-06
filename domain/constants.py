"""Domain-level constants for schema, pagination, and business defaults."""

from typing import Final


class TableName:
    """Relational table names for ORM models and association mappings."""

    PERMISSIONS: Final[str] = "permissions"
    ROLES: Final[str] = "roles"
    ROLE_PERMISSIONS: Final[str] = "role_permissions"
    USERS: Final[str] = "users"
    PATIENTS: Final[str] = "patients"
    ROUTING_RULES: Final[str] = "routing_rules"
    PATIENT_WORKFLOWS: Final[str] = "patient_workflows"
    CLINICAL_RECORDS: Final[str] = "clinical_records"


class ForeignKeyAction:
    """Referential integrity actions for foreign key constraints."""

    CASCADE: Final[str] = "CASCADE"
    RESTRICT: Final[str] = "RESTRICT"
    SET_NULL: Final[str] = "SET NULL"


class ColumnLength:
    """Maximum varchar lengths for relational columns."""

    USERNAME: Final[int] = 150
    PASSWORD_HASH: Final[int] = 255
    ENTITY_NAME: Final[int] = 255
    PERMISSION_NAME: Final[int] = 100
    ROLE_NAME: Final[int] = 100
    DESCRIPTION: Final[int] = 500
    RECORD_TYPE: Final[int] = 100
    TITLE: Final[int] = 255
    DEPARTMENT: Final[int] = 100
    CONDITION_EXPRESSION: Final[int] = 1000


class PaginationDefaults:
    """Default pagination boundaries for repository queries."""

    SKIP: Final[int] = 0
    LIMIT: Final[int] = 100
    MAX_LIMIT: Final[int] = 1000


class RoutingRuleDefaults:
    """Default values for routing rule engine records."""

    PRIORITY: Final[int] = 0
    IS_ACTIVE: Final[bool] = True


def foreign_key_reference(table_name: str, column: str = "id") -> str:
    """Build a dotted foreign-key reference string.

    Args:
        table_name: Target table name.
        column: Target column name.

    Returns:
        Dotted reference in the form ``table.column``.
    """
    return f"{table_name}.{column}"
