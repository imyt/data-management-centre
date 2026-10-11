"""Domain Exceptions.

Pure business rule exceptions with zero HTTP or framework dependencies.
"""


class DomainException(Exception):
    """Base domain exception."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class EntityNotFoundException(DomainException):
    """Raised when an entity is not found in the domain."""
    pass


class ConcurrencyLockException(DomainException):
    """Raised when an asset is under exclusive revision lease by another user."""
    pass


class DraftNotFoundException(DomainException):
    """Raised when an operation requires an active working draft that does not exist."""
    pass


class UnauthorizedDraftModificationException(DomainException):
    """Raised when a user attempts to modify or publish a draft locked by another user."""
    pass


class ValidationException(DomainException):
    """Raised when domain invariant validation fails."""
    pass


class WorkflowExecutionException(DomainException):
    """Raised when an invalid workflow transition or rule violation occurs."""
    pass


class DependencyConflictException(DomainException):
    """Raised when an entity deletion is blocked by referential bindings (e.g. active dataset in data movement)."""
    def __init__(self, message: str, blocking_entities: list = None):
        super().__init__(message)
        self.blocking_entities = blocking_entities or []

