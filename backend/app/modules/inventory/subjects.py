"""What policy can select on: the attributes of assets, data stores and applications.

Policy never reads inventory tables. It asks `SubjectCatalog` which attributes a subject type has
(the vocabulary a selector is written in) and for the current facts of subjects, so a selector can
only ever name an attribute, never an application or an asset (FR-P2).
"""

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from app.modules.inventory.domain import (
    AssetType,
    Criticality,
    DataStoreType,
    EnvironmentType,
    Hosting,
    LifecycleStatus,
    OwnershipRole,
)
from app.modules.inventory.models import (
    Application,
    Asset,
    DataCategory,
    DataStore,
    Domain,
    Region,
    RetentionPolicy,
)
from app.modules.inventory.repository import InventoryRepository, ReferenceModel

SUBJECT_CHANGED = "inventory.subject_changed"
"""Outbox event: a subject's attributes or the people accountable for it may have changed.
Payload: `subject_type`, `subject_id`."""


class SubjectType(StrEnum):
    ASSET = "asset"
    DATA_STORE = "data_store"
    APPLICATION = "application"


type AttributeValue = bool | str


@dataclass(frozen=True)
class ValueOption:
    value: str
    label: str


@dataclass(frozen=True)
class AttributeSpec:
    """One attribute selectors may use. `options` is empty for booleans."""

    name: str
    label: str
    kind: str  # "boolean" or "choice"
    options: tuple[ValueOption, ...] = ()

    def label_for(self, value: AttributeValue) -> str:
        if isinstance(value, bool):
            return "yes" if value else "no"
        return next((o.label for o in self.options if o.value == value), value)


@dataclass(frozen=True)
class SubjectFacts:
    """A subject as policy sees it: its attributes and who is accountable and responsible.

    `attributes` leaves out an attribute the subject has no value for (an asset with no data
    category), so equality never matches it.
    """

    subject_type: SubjectType
    subject_id: uuid.UUID
    name: str
    domain_id: uuid.UUID
    attributes: dict[str, AttributeValue]
    accountable_id: uuid.UUID | None = None
    responsible_id: uuid.UUID | None = None


def _choice(name: str, label: str, values: type[StrEnum]) -> AttributeSpec:
    options = tuple(ValueOption(v.value, v.value.replace("_", " ").capitalize()) for v in values)
    return AttributeSpec(name, label, "choice", options)


_BOOLEAN = "boolean"

# Attributes backed by reference data get their options from the database.
_REFERENCE: dict[tuple[SubjectType, str], ReferenceModel] = {
    (SubjectType.ASSET, "domain"): Domain,
    (SubjectType.ASSET, "data_category"): DataCategory,
    (SubjectType.ASSET, "retention_policy"): RetentionPolicy,
    (SubjectType.DATA_STORE, "domain"): Domain,
    (SubjectType.DATA_STORE, "region"): Region,
    (SubjectType.APPLICATION, "domain"): Domain,
}

_STATIC: dict[SubjectType, tuple[AttributeSpec, ...]] = {
    SubjectType.ASSET: (
        _choice("type", "Type", AssetType),
        AttributeSpec("domain", "Domain", "choice"),
        AttributeSpec("data_category", "Data category", "choice"),
        AttributeSpec("is_stored", "Stored", _BOOLEAN),
        AttributeSpec("retention_policy", "Retention policy", "choice"),
        AttributeSpec("contains_pii", "Contains personal data", _BOOLEAN),
        AttributeSpec("contains_cde", "Contains a critical data element", _BOOLEAN),
    ),
    SubjectType.DATA_STORE: (
        _choice("type", "Type", DataStoreType),
        _choice("environment_type", "Environment", EnvironmentType),
        AttributeSpec("domain", "Domain", "choice"),
        AttributeSpec("region", "Region", "choice"),
    ),
    SubjectType.APPLICATION: (
        _choice("criticality", "Criticality", Criticality),
        _choice("hosting", "Hosting", Hosting),
        _choice("lifecycle_status", "Lifecycle", LifecycleStatus),
        AttributeSpec("domain", "Domain", "choice"),
    ),
}


class SubjectCatalog:
    def __init__(self, session: Session) -> None:
        self._repository = InventoryRepository(session)

    def attributes(self, subject_type: SubjectType) -> list[AttributeSpec]:
        """The attributes of a subject type, with their options."""
        specs = []
        for spec in _STATIC[subject_type]:
            model = _REFERENCE.get((subject_type, spec.name))
            if model is not None:
                options = tuple(
                    ValueOption(item.code, item.name)
                    for item in self._repository.list_reference(model)
                )
                spec = AttributeSpec(spec.name, spec.label, spec.kind, options)
            specs.append(spec)
        return specs

    def facts(
        self, subject_type: SubjectType, subject_ids: list[uuid.UUID] | None = None
    ) -> list[SubjectFacts]:
        """Current facts of the given subjects, or of every subject of the type."""
        if subject_type is SubjectType.ASSET:
            return [_asset_facts(a) for a in self._repository.assets_for_facts(subject_ids)]
        if subject_type is SubjectType.DATA_STORE:
            return [_store_facts(s) for s in self._repository.data_stores_for_facts(subject_ids)]
        return [_application_facts(a) for a in self._repository.applications_for_facts(subject_ids)]


def _present(attributes: dict[str, Any]) -> dict[str, AttributeValue]:
    return {k: v for k, v in attributes.items() if v is not None}


def _asset_facts(asset: Asset) -> SubjectFacts:
    holders = {o.role: o.user_id for o in asset.ownerships}
    return SubjectFacts(
        subject_type=SubjectType.ASSET,
        subject_id=asset.id,
        name=asset.name,
        domain_id=asset.domain_id,
        attributes=_present(
            {
                "type": asset.type,
                "domain": asset.domain.code,
                "data_category": asset.data_category.code if asset.data_category else None,
                "is_stored": asset.is_stored,
                "retention_policy": asset.retention_policy.code if asset.retention_policy else None,
                "contains_pii": any(e.is_pii for e in asset.data_elements),
                "contains_cde": any(e.is_cde for e in asset.data_elements),
            }
        ),
        accountable_id=holders.get(OwnershipRole.OWNER),
        responsible_id=holders.get(OwnershipRole.STEWARD),
    )


def _store_facts(store: DataStore) -> SubjectFacts:
    environment = store.environment
    application = environment.application
    return SubjectFacts(
        subject_type=SubjectType.DATA_STORE,
        subject_id=store.id,
        name=f"{application.name} / {store.name}",
        domain_id=application.domain_id,
        attributes=_present(
            {
                "type": store.type,
                "environment_type": environment.type,
                "domain": application.domain.code,
                "region": store.region.code,
            }
        ),
        accountable_id=application.app_owner_id,
        responsible_id=application.tech_owner_id,
    )


def _application_facts(application: Application) -> SubjectFacts:
    return SubjectFacts(
        subject_type=SubjectType.APPLICATION,
        subject_id=application.id,
        name=application.name,
        domain_id=application.domain_id,
        attributes=_present(
            {
                "criticality": application.criticality,
                "hosting": application.hosting,
                "lifecycle_status": application.lifecycle_status,
                "domain": application.domain.code,
            }
        ),
        accountable_id=application.app_owner_id,
        responsible_id=application.tech_owner_id,
    )
