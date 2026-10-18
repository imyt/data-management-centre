"""Maps domain errors and framework errors to RFC 9457 problem details."""

import logging
import uuid
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import (
    ConflictError,
    DomainError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
)
from app.core.schemas import PROBLEM_JSON, ProblemDetail, ValidationIssue

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"

_DOMAIN_STATUS: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidInputError: status.HTTP_400_BAD_REQUEST,
    ConflictError: status.HTTP_409_CONFLICT,
    UnauthenticatedError: status.HTTP_401_UNAUTHORIZED,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
}

_DOMAIN_TITLE: dict[str, str] = {
    NotFoundError.code: "Not found",
    InvalidInputError.code: "Invalid input",
    ConflictError.code: "Conflict",
    UnauthenticatedError.code: "Not signed in",
    PermissionDeniedError.code: "Permission denied",
}

_RESERVED_MEMBERS = frozenset(ProblemDetail.model_fields)


class RequestIdMiddleware:
    """Takes X-Request-ID from the request (or makes one) and echoes it on the response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        header = REQUEST_ID_HEADER.lower().encode()
        incoming = dict(scope["headers"]).get(header, b"").decode("latin-1")[:64]
        request_id = incoming or uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).append((header, request_id.encode("latin-1")))
            await send(message)

        await self.app(scope, receive, send_with_id)


def problem_type(code: str) -> str:
    """The problem `type` URI for a stable error code."""
    return f"urn:dmc:problem:{code}"


def _problem(
    request: Request,
    status_code: int,
    *,
    type_: str = "about:blank",
    title: str | None = None,
    detail: str | None = None,
    errors: list[ValidationIssue] | None = None,
    extensions: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    extra = jsonable_encoder(extensions) if isinstance(extensions, dict) else {}
    body = ProblemDetail(
        type=type_,
        title=title or HTTPStatus(status_code).phrase,
        status=status_code,
        detail=detail,
        instance=request.url.path,
        request_id=getattr(request.state, "request_id", ""),
        errors=errors,
        **{k: v for k, v in extra.items() if k not in _RESERVED_MEMBERS},
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json", exclude_none=True),
        media_type=PROBLEM_JSON,
        headers=headers,
    )


def _document_problem_media_type(app: FastAPI) -> None:
    """FastAPI documents every response model as application/json; errors are problem+json."""
    generate = app.openapi

    def openapi() -> dict[str, Any]:
        spec = generate()
        for path in spec.get("paths", {}).values():
            for operation in path.values():
                for code, response in operation.get("responses", {}).items():
                    content = response.get("content", {})
                    if str(code)[0] in "45" and "application/json" in content:
                        content[PROBLEM_JSON] = content.pop("application/json")
        return spec

    app.openapi = openapi  # type: ignore[method-assign]


def register_error_handlers(app: FastAPI) -> None:
    _document_problem_media_type(app)

    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError) -> JSONResponse:
        status_code = next(
            (code for cls, code in _DOMAIN_STATUS.items() if isinstance(exc, cls)),
            status.HTTP_400_BAD_REQUEST,
        )
        return _problem(
            request,
            status_code,
            type_=problem_type(exc.code),
            title=_DOMAIN_TITLE.get(exc.code, HTTPStatus(status_code).phrase),
            detail=exc.message,
            extensions=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [ValidationIssue(loc=e["loc"], msg=e["msg"], type=e["type"]) for e in exc.errors()]
        return _problem(
            request,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            type_=problem_type("validation_error"),
            title="Validation error",
            detail="Some fields are not valid.",
            errors=errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problem(request, exc.status_code, detail=str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "")
        logger.exception("Unhandled error", extra={"request_id": request_id})
        return _problem(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong. Try again, or contact support with the request ID.",
            # Unhandled errors are answered outside RequestIdMiddleware, so echo the ID here.
            headers={REQUEST_ID_HEADER: request_id},
        )
