"""The seven dev personas, one per role in PRD.md §2 (ADR 0004 §7). Seeded by `dmc-seed`."""

import uuid
from dataclasses import dataclass

from app.core.auth import Role

# Inventory seeds its domains with these ids, so persona scopes resolve to real domains.
CUSTOMER = uuid.UUID("0199f000-0000-7000-8000-000000000001")
FINANCE = uuid.UUID("0199f000-0000-7000-8000-000000000002")
PEOPLE = uuid.UUID("0199f000-0000-7000-8000-000000000003")


@dataclass(frozen=True)
class Persona:
    username: str
    display_name: str
    role: Role
    domain_ids: frozenset[uuid.UUID] | None  # None: every domain


PERSONAS: tuple[Persona, ...] = (
    Persona("priya.raman", "Priya Raman", Role.DATA_OWNER, frozenset({CUSTOMER})),
    Persona("marcus.webb", "Marcus Webb", Role.APPLICATION_OWNER, frozenset({CUSTOMER, FINANCE})),
    Persona("lena.okafor", "Lena Okafor", Role.DATA_STEWARD, frozenset({CUSTOMER})),
    Persona("tomas.silva", "Tomás Silva", Role.PROCESS_OWNER, frozenset({FINANCE})),
    Persona("hannah.becker", "Hannah Becker", Role.GOVERNANCE, None),
    Persona("david.chen", "David Chen", Role.LEADERSHIP, None),
    Persona("sofia.marin", "Sofia Marin", Role.AUDITOR, None),
)

# Acts for requests that name no user, in local and dev only.
DEFAULT_PERSONA = "hannah.becker"
