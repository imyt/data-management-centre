"""Schemas shared by every API: the response envelope and the problem details error shape."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Meta(BaseModel):
    """Freshness of the data in a response, when the data was derived by an evaluation."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    evaluated_at: datetime | None = Field(
        default=None, description="When the data was last evaluated, if it is derived."
    )
    stale_after: datetime | None = Field(
        default=None, description="When the data should be treated as stale."
    )


class ListMeta(Meta):
    """Meta for a list: freshness plus cursor paging."""

    next_cursor: str | None = Field(
        default=None, description="Pass as `cursor` to get the next page; null on the last page."
    )
    total: int | None = Field(default=None, description="Total matching items, when cheap.")


class Envelope[DataT](BaseModel):
    """The shared base of every response model (ARCHITECTURE §8).

    Subclass with a concrete type so the schema gets a clean name.
    """

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    data: DataT
    allowed_actions: list[str] = Field(
        default_factory=list, description="Actions the caller may take on `data` right now."
    )
    meta: Meta = Field(default_factory=Meta)


class ListEnvelope[ItemT](Envelope[list[ItemT]]):
    """A page of a list. Subclass with a concrete item type so the schema gets a clean name."""

    meta: ListMeta = Field(default_factory=ListMeta)


PROBLEM_JSON = "application/problem+json"


class ValidationIssue(BaseModel):
    """One field that failed request validation."""

    loc: list[str | int] = Field(description="Where the field is, e.g. `['query', 'limit']`.")
    msg: str = Field(description="Plain-language message.")
    type: str = Field(description="Stable, machine-readable kind of failure.")


class ProblemDetail(BaseModel):
    """The one error shape every endpoint returns: RFC 9457 problem details.

    Structured context from a domain error is added as extension members.
    """

    model_config = ConfigDict(extra="allow")

    type: str = Field(
        default="about:blank",
        description="URI identifying the problem type; `urn:dmc:problem:<code>` for domain errors.",
    )
    title: str = Field(description="Short summary of the problem type.")
    status: int = Field(description="HTTP status code.")
    detail: str | None = Field(
        default=None, description="Plain-language explanation safe to show to the user."
    )
    instance: str | None = Field(default=None, description="The request path that failed.")
    request_id: str = Field(description="Matches the X-Request-ID response header.")
    errors: list[ValidationIssue] | None = Field(
        default=None, description="Fields that failed validation (422 only)."
    )


_ERROR_DESCRIPTIONS = {
    400: "Invalid input",
    401: "Not signed in",
    403: "Permission denied",
    404: "Not found",
    409: "Conflict",
    422: "Validation error",
    501: "Not implemented",
    503: "Service unavailable",
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` entries documenting `ProblemDetail` for the given status codes."""
    return {
        code: {"model": ProblemDetail, "description": _ERROR_DESCRIPTIONS[code]}
        for code in status_codes
    }
