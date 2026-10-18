import pytest
from sqlalchemy import Connection, text

from app.core.auth import Role
from app.core.db import Database
from app.core.errors import ConflictError
from app.modules.identity.personas import CUSTOMER, PERSONAS
from app.modules.identity.service import IdentityDirectory, IdentityService, NewUser, User


def test_seeding_is_audited_and_idempotent(database: Database, db_connection: Connection) -> None:
    with database.transaction() as session:
        first = IdentityService(session).seed_personas()
        again = IdentityService(session).seed_personas()

    events = db_connection.execute(
        text("SELECT actor, subject_id, after FROM audit.audit_event WHERE action = :a"),
        {"a": "identity.user_created"},
    ).all()
    assert len(first) == len(PERSONAS) and again == []
    assert {e.subject_id for e in events} == {str(u.id) for u in first}
    assert {e.actor for e in events} == {"system:seed"}


def test_directory_resolves_active_users_to_principals(
    database: Database, personas: dict[str, User]
) -> None:
    with database.transaction() as session:
        priya = IdentityDirectory().principal_for(session, "priya.raman")
        nobody = IdentityDirectory().principal_for(session, "nobody")

    assert priya is not None and nobody is None
    assert priya.user_id == personas["priya.raman"].id
    assert priya.roles == {Role.DATA_OWNER}
    assert priya.domain_ids == {CUSTOMER}
    assert priya.actor == f"user:{priya.user_id}"


def test_usernames_are_unique(database: Database, personas: dict[str, User]) -> None:
    with database.transaction() as session, pytest.raises(ConflictError):
        IdentityService(session).create_user(
            NewUser("priya.raman", "Another Priya", frozenset({Role.AUDITOR}), None),
            actor="user:test",
        )
