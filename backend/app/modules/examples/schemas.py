"""Pydantic read models and response envelopes for the examples API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.schemas import Envelope, ListEnvelope
from app.modules.examples.domain import ExampleStatus


class ExampleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: ExampleStatus
    created_at: datetime


class ExampleResponse(Envelope[ExampleRead]):
    pass


class ExamplePage(ListEnvelope[ExampleRead]):
    pass
