"""Domain errors. Services raise these; the API app maps each one to an HTTP status."""

from typing import Any


class DomainError(Exception):
    """Base class for errors a caller can act on. `code` is stable and machine-readable."""

    code = "domain_error"

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(DomainError):
    code = "not_found"


class InvalidInputError(DomainError):
    code = "invalid_input"


class ConflictError(DomainError):
    code = "conflict"


class UnauthenticatedError(DomainError):
    """The caller could not be identified."""

    code = "unauthenticated"


class PermissionDeniedError(DomainError):
    code = "permission_denied"
