"""Configured page lookup relations; SQL identifiers never come from requests."""

import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from .baseline_store import StoreError


@dataclass(frozen=True)
class ReadSources:
    assets: str
    owners: str

    @classmethod
    def from_config(cls, values):
        if set(values) != {"assets", "owners"}:
            raise ValueError("read_sources_configuration_incomplete")
        for key in ("assets", "owners"):
            if not isinstance(values[key], str) or not re.fullmatch(r"[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*", values[key]):
                raise ValueError("read_source_identifier_invalid")
        return cls(**values)

    def relation(self, key):
        schema, name = getattr(self, key).split(".")
        return f'"{schema}"."{name}"'

    async def check(self, connection):
        requirements = []
        for key, columns in (
            ("assets", ("id", "tenant_id", "name", "fqdn", "asset_type", "tags", "criticality", "os", "os_version", "ip_addresses")),
            ("owners", ("id", "tenant_id", "username")),
        ):
            schema, name = getattr(self, key).split(".")
            row = (await connection.execute(text("""SELECT bool_and(
                    has_column_privilege(current_user,c.oid,col,'SELECT')) AS readable
                    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace,
                    unnest(CAST(:columns AS text[])) AS col
                    WHERE n.nspname=:schema AND c.relname=:name"""),
                    {"schema": schema, "name": name, "columns": list(columns)})).mappings().one()
            ready = bool(row["readable"])
            requirements.append({"dependency": key, "ready": ready})
            if ready:
                # Parse/authorize the real projection without reading any rows.
                # A configured relation with an outdated shape is not ready.
                projection = ",".join('"' + c + '"' for c in columns)
                await connection.execute(text(f"SELECT {projection} FROM {self.relation(key)} LIMIT 0"))
        return requirements


def lookup_error(exc):
    """Expose an operational dependency failure without SQL, DSN or source rows."""
    if not isinstance(exc, DBAPIError):
        raise exc
    cause = exc.orig
    state = getattr(cause, "sqlstate", None) or getattr(cause, "pgcode", None)
    if not state and cause.__cause__:
        state = getattr(cause.__cause__, "sqlstate", None)
    codes = {"42501": "read_dependency_permission_denied", "42P01": "read_dependency_missing",
             "42883": "read_dependency_missing", "42703": "read_dependency_schema_mismatch"}
    if state in codes:
        raise StoreError(codes[state], 503) from None
    raise exc
