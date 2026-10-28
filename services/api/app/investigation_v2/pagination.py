"""Small scope-bound cursors for investigation history reads."""
import base64
import binascii
from datetime import datetime
import json
from uuid import UUID

from fastapi import HTTPException


def encode_cursor(at: datetime, identity: UUID, scope: str) -> str:
    value = json.dumps([at.isoformat(), str(identity), scope]).encode()
    return base64.urlsafe_b64encode(value).decode()


def decode_cursor(value: str | None, scope: str):
    if value is None:
        return None
    try:
        if len(value) > 2048:
            raise ValueError()
        at, identity, saved_scope = json.loads(base64.b64decode(value, altchars=b'-_', validate=True))
        at, identity = datetime.fromisoformat(at), UUID(identity)
        if at.tzinfo is None or saved_scope != scope:
            raise ValueError()
        return at, identity
    except (ValueError, TypeError, AttributeError, binascii.Error):
        raise HTTPException(422, "invalid_cursor") from None
