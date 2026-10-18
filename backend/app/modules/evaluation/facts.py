"""The facts evaluators read, taken from the modules that own them through their services."""

import uuid

from sqlalchemy.orm import Session

from app.modules.connectors.service import ConnectorsService, MeasurementError, OldestRecord
from app.modules.evaluation.domain import FactsUnavailableError
from app.modules.inventory.service import AssetRetention, AssetService


class ModuleFacts:
    def __init__(self, session: Session, connectors: ConnectorsService | None = None) -> None:
        self._assets = AssetService(session)
        self._connectors = connectors or ConnectorsService(session)

    def asset_retention(self, asset_id: uuid.UUID) -> AssetRetention | None:
        return self._assets.retention_of(asset_id)

    def oldest_record(self, asset_id: uuid.UUID) -> OldestRecord:
        try:
            return self._connectors.oldest_record_of_asset(asset_id)
        except MeasurementError as exc:
            raise FactsUnavailableError(str(exc)) from exc
