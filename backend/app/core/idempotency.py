"""`Idempotency-Key` for writes that clients may retry (ARCHITECTURE §8, ADR 0009).

A route opts in by taking `IdempotencyDep` and returning its response through `record`:

    @router.post(..., status_code=202, response_model=JobResponse)
    def start_export(
        request: Request, session: SessionDep, principal: PrincipalDep,
        idempotency: IdempotencyDep,
    ) -> JSONResponse:
        job = enqueue(session, "reporting.export", {...}, created_by=principal.actor)
        return idempotency.record(accepted(request, job))

Without the header nothing changes. With it, the key is stored, per caller, with a hash of the
request (method, path, query and body) and, through `record`, the response, all in the
request's own transaction, for 24 hours:

- the same key and request again → the stored response, with `Idempotent-Replayed: true`;
- the same key with a different request → 409 problem details;
- a request that fails rolls back, key included, so the client can retry it.

A second request with a key that is still in flight waits for the first to commit (the key's
row is locked by its insert), then replays its response.
"""

import hashlib
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, Header, Request, Response
from sqlalchemy import DateTime, Index, Integer, String, Text, delete, func
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.auth import PrincipalDep
from app.core.db import Base, SessionDep
from app.core.errors import ConflictError

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
REPLAYED_HEADER = "Idempotent-Replayed"
TTL = timedelta(hours=24)
# Headers worth replaying; the rest (request id, date, length) belong to the new response.
_REPLAYED_HEADERS = ("content-type", "location")


class IdempotencyKey(Base):
    __tablename__ = "idempotency_key"
    __table_args__ = (Index("ix_idempotency_key_expires_at", "expires_at"), {"schema": "platform"})

    # Keys are per caller (`Principal.actor`): one user's key never replays another's response.
    owner: Mapped[str] = mapped_column(Text, primary_key=True)
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_headers: Mapped[dict[str, str] | None] = mapped_column(JSONB(none_as_null=True))
    response_body: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IdempotentReplay(Exception):
    """Raised before the route runs; the error handlers answer with the stored response."""

    def __init__(self, stored: IdempotencyKey) -> None:
        super().__init__(stored.key)
        # Copied now: the request's transaction rolls back before the handler answers.
        self.status_code = stored.response_status or 200
        self.headers = {**(stored.response_headers or {}), REPLAYED_HEADER: "true"}
        self.body = stored.response_body

    def response(self) -> Response:
        return Response(content=self.body, status_code=self.status_code, headers=self.headers)


class Idempotency:
    """What a route gets from `IdempotencyDep`. Inert when the request carried no key."""

    def __init__(self, stored: IdempotencyKey | None) -> None:
        self._stored = stored
        self.recorded = False

    @property
    def key(self) -> str | None:
        return self._stored.key if self._stored else None

    def record[ResponseT: Response](self, response: ResponseT) -> ResponseT:
        """Store the response to replay for this key, in the request's transaction."""
        if self._stored is not None:
            self._stored.response_status = response.status_code
            self._stored.response_body = bytes(response.body).decode()
            self._stored.response_headers = {
                name: response.headers[name]
                for name in _REPLAYED_HEADERS
                if name in response.headers
            }
        self.recorded = True
        return response


async def _request_hash(request: Request) -> str:
    digest = hashlib.sha256()
    for part in (request.method, request.url.path, request.url.query):
        digest.update(part.encode())
        digest.update(b"\n")
    digest.update(await request.body())
    return digest.hexdigest()


def _idempotency(
    session: SessionDep,
    principal: PrincipalDep,
    request_hash: Annotated[str, Depends(_request_hash)],
    key: Annotated[
        str | None,
        Header(
            alias=IDEMPOTENCY_KEY_HEADER,
            min_length=1,
            max_length=255,
            description="Send a unique value (e.g. a UUID) to make retries of this request safe.",
        ),
    ] = None,
) -> Iterator[Idempotency]:
    if key is None:
        yield Idempotency(None)
        return
    _claim(session, principal.actor, key, request_hash)
    idempotency = Idempotency(session.get(IdempotencyKey, (principal.actor, key)))
    yield idempotency
    if not idempotency.recorded:
        raise RuntimeError("The route takes an Idempotency-Key but did not call record()")


def _claim(session: Session, owner: str, key: str, request_hash: str) -> None:
    """Insert the key, or raise: a replay of the stored response, or a conflict."""
    session.execute(
        delete(IdempotencyKey).where(
            IdempotencyKey.owner == owner,
            IdempotencyKey.key == key,
            IdempotencyKey.expires_at <= func.now(),
        )
    )
    inserted = session.scalars(
        insert(IdempotencyKey)
        .values(owner=owner, key=key, request_hash=request_hash, expires_at=func.now() + TTL)
        .on_conflict_do_nothing(index_elements=[IdempotencyKey.owner, IdempotencyKey.key])
        .returning(IdempotencyKey.key)
    ).one_or_none()
    if inserted is not None:
        return
    stored = session.get(IdempotencyKey, (owner, key), populate_existing=True)
    if stored is None:  # expired and purged between the two statements
        raise ConflictError("Retry the request.", details={"idempotency_key": key})
    if stored.request_hash != request_hash:
        raise ConflictError(
            "This Idempotency-Key was already used for a different request. "
            "Send a new key for a new request.",
            details={"idempotency_key": key},
        )
    raise IdempotentReplay(stored)


IdempotencyDep = Annotated[Idempotency, Depends(_idempotency, scope="function")]
