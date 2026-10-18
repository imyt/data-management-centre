"""Cursor pagination helpers. Cursors are opaque to clients."""

import base64
import binascii
from dataclasses import dataclass

from app.core.errors import InvalidInputError


@dataclass(frozen=True, slots=True)
class PageResult[T]:
    """One page of results as returned by a service."""

    items: list[T]
    next_cursor: str | None
    total: int | None = None


def encode_cursor(key: str) -> str:
    return base64.urlsafe_b64encode(key.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> str:
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        return base64.b64decode(padded, altchars=b"-_", validate=True).decode()
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise InvalidInputError("The cursor is not valid.", details={"cursor": cursor}) from exc
