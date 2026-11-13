"""SQL selection and opaque seek cursors; never calls an HTTP or model service."""
import base64
import binascii
from uuid import UUID

from sqlalchemy import and_, case, or_

from .baseline_store import StoreError, digest
from .list_query_contracts import ListCursor
from .program_facts import RANK


def title_match(table, value):
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    predicate = table.c.title.ilike("%" + escaped + "%", escape="\\")
    try:
        return or_(predicate, table.c.id == UUID(value))
    except ValueError:
        return predicate


def severity_rank(column):
    return case(*[(column == value, rank) for value, rank in RANK.items()], else_=None)


def time_filters(column, query):
    return ([column >= query.time_from] if query.time_from is not None else []) + (
        [column < query.time_to] if query.time_to is not None else [])


def fingerprint(tenant, kind, query):
    return digest({"tenant_id": str(tenant), "kind": kind,
        **query.model_dump(mode="json", exclude={"limit", "cursor", "before_id"})})


def read_cursor(tenant, kind, query, sort_by):
    if query.cursor is None:
        return None
    try:
        raw = base64.b64decode(query.cursor, altchars=b"-_", validate=True)
        point = ListCursor.model_validate_json(raw)
        if (sort_by == "severity" and point.at is not None) or (sort_by != "severity" and point.rank is not None):
            raise ValueError("wrong_sort_value")
    except (ValueError, TypeError, binascii.Error):
        raise StoreError("invalid_list_cursor", 422) from None
    if point.kind != kind or point.sort_by != sort_by or point.filter_fingerprint != fingerprint(tenant, kind, query):
        raise StoreError("list_cursor_filters_changed", 422)
    return point


def write_cursor(tenant, kind, query, sort_by, identity, value):
    point = ListCursor(kind=kind, sort_by=sort_by, id=identity,
        filter_fingerprint=fingerprint(tenant, kind, query),
        **({"rank": value} if sort_by == "severity" else {"at": value}))
    return base64.urlsafe_b64encode(point.model_dump_json().encode()).decode()


def seek(column, identity, value, point_id, order):
    after_id = identity > point_id if order == "asc" else identity < point_id
    if value is None:
        return and_(column.is_(None), after_id)
    after_value = column > value if order == "asc" else column < value
    return or_(after_value, and_(column == value, after_id), column.is_(None))


def ordering(column, identity, order):
    return ((column.asc().nulls_last(), identity.asc()) if order == "asc"
            else (column.desc().nulls_last(), identity.desc()))
