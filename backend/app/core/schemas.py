"""Schemas shared by every API: the error shape and the list page shape."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """The one error shape every endpoint returns."""

    code: str = Field(description="Stable, machine-readable error code.")
    message: str = Field(description="Plain-language message safe to show to the user.")
    details: Any = Field(default=None, description="Optional structured context.")
    request_id: str = Field(description="Matches the X-Request-ID response header.")


class Page[T](BaseModel):
    """A page of a list. Subclass with a concrete item type so the schema gets a clean name."""

    items: list[T]
    next_cursor: str | None = Field(description="Pass as `cursor` to get the next page.")
    total: int | None = Field(default=None, description="Total matching items, when cheap.")


_ERROR_DESCRIPTIONS = {
    400: "Invalid input",
    403: "Permission denied",
    404: "Not found",
    409: "Conflict",
    422: "Validation error",
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` entries documenting `ErrorResponse` for the given status codes."""
    return {
        code: {"model": ErrorResponse, "description": _ERROR_DESCRIPTIONS[code]}
        for code in status_codes
    }
