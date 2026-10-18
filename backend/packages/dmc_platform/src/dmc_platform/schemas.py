"""Pydantic read models for the platform API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from dmc_common.public import Page
from dmc_platform.domain.example import ExampleStatus


class HealthRead(BaseModel):
    status: Literal["ok"]


class ExampleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: ExampleStatus
    created_at: datetime


class ExamplePage(Page[ExampleRead]):
    pass
