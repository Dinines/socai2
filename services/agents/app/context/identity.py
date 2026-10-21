"""Who is behind the account this alert names, where a connector provides it.

Gap-closure Phase 6.3, agents half.

A verdict about an account is a different verdict depending on whose account
it is. A contractor whose engagement ended last month authenticating from a
new country is not the same alert as a support engineer on rotation doing the
same thing, and triage has had no way to tell them apart.

The data is already there for any tenant that has imported a directory or a
CMDB: ``POST /graph/context/import`` writes ``Employee``, ``Department`` and
``Identity`` nodes, and ``incident_context.py`` already reads them for an
escalated alert. What did not exist was a version of the question triage can
ask, because that traversal starts at an ``Alert`` node and triage runs before
one exists. This reads by account name instead.

Nothing is inferred when the tenant has imported nothing. An empty result is
an empty block, not a statement that the principal is unknown.

The freeze here is weaker than the other two, and says so
---------------------------------------------------------
An ``Employee`` node carries ``updated_at``, set when the snapshot was
imported. That is an import stamp, not a business-effective date, and the
difference matters exactly where this source is most useful: a record imported
yesterday may describe somebody who left last year, and a record imported
before the split may have been updated in place since.

Frozen reads require a native, comparable import stamp and refuse later,
missing or unsupported stamps. Live reads may retain unknown stamps. Neither
case establishes the history of the holder or linked relations: the API counts **every row it serves** as
untestable, because surviving an import-time cutoff is not evidence that the
fact predates the split. Both numbers reach the replay report.

That is the same treatment organisation-memory statements get, and for the
same reason: the existing precedent publishes ``statements_without_timestamp``
rather than claiming a freeze tighter than the data supports. A source whose
untestable count is always the whole set is not a reason to stop publishing
the count; it is the reason to publish it.

Containment
-----------
First-party. A display name, a title, a department and a manager come from the
tenant's own directory import, so this is sanitised and capped rather than
nonce-fenced, like organisation memory and unlike a knowledge-base article.
The cap is not ceremony: a display name is a free-text field in every
directory product, and the prompt budget is shared with the evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any, Literal, TypedDict

import httpx
import structlog

from app.context.organisation_memory import _credential
from app.investigator.prompt_sanitizer import sanitize_text

logger = structlog.get_logger()

__all__ = ["MAX_IDENTITIES_IN_PROMPT", "IdentityContext", "IdentityContextRead", "accounts_for", "basis",
           "clear_cache", "enabled", "fetch_identity_context", "render_for_prompt", "render_read_status",
           "make_read", "enforce_cutoff"]
_API_URL = os.getenv("API_SERVICE_URL", "http://api:8000")
_TIMEOUT_S = float(os.getenv("AISOC_TRIAGE_IDENTITY_TIMEOUT_S", "5"))
MAX_IDENTITIES_IN_PROMPT = int(os.getenv("AISOC_TRIAGE_IDENTITY_TOP_N", "5"))
_MAX_FIELD_CHARS = 120
_MAX_PROMPT_CHARS = 3000
_CACHE_TTL_S = float(os.getenv("AISOC_TRIAGE_IDENTITY_TTL_S", "300"))
_SOURCE = "api.graph.identity-context"
_GRAPH_FAILURE_REASONS = {"graph_not_configured", "graph_timeout", "graph_auth_failed", "graph_unavailable",
                          "graph_query_failed", "invalid_source_response"}
_SOURCE_FIELDS = (
    "identity_id", "identity_id_kind", "employee_id", "employee_id_kind", "department_id", "department_id_kind",
    "manager_id", "manager_id_kind", "account", "provider", "employee", "title", "is_active", "employment_type",
    "start_date", "end_date", "imported_at", "imported_at_status", "imported_at_raw_sha256", "department", "manager",
    "manager_email", "employee_linked", "relationship_source",
)
_COUNTS = ("candidate_count", "eligible_count", "truncated_count", "excluded_after_cutoff",
           "excluded_unverifiable_import", "import_timestamp_missing", "without_timestamp")
_DISPLAY_LIMITS = {"account": 120, "provider": 120, "employee": 120, "title": 120, "department": 120,
                   "manager": 120, "employment_type": 40, "end_date": 40}
_HEADER = "Directory context for the principals in this alert, from this tenant's own imported HR or identity data:\n"
_ADVISORY = (
    "\nThis describes the account holder, not the activity. It is a reason to weigh the "
    "activity differently, never a verdict on its own: an inactive account authenticating is "
    "worth escalating, and a senior title is not evidence that anything was authorised. The "
    "record reflects the last directory import and may be out of date."
)
_cache: dict[tuple[Any, ...], tuple[float, str, dict[str, Any]]] = {}


def enabled() -> bool:
    return os.getenv("AISOC_TRIAGE_IDENTITY_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}


def clear_cache() -> None:
    _cache.clear()


def _now() -> datetime:
    return datetime.now(UTC)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_hash(tenant_id: str, row: Mapping[str, Any]) -> str:
    value = {"tenant_id": tenant_id, **{key: row[key] for key in _SOURCE_FIELDS}}
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def _stamp(value: datetime | None) -> str | None:
    return (value.replace(tzinfo=UTC) if value.tzinfo is None else value).astimezone(UTC).isoformat() if value is not None else None


def _date(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("missing import timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("import timestamp must be UTC")
    return parsed


class IdentityContextRead(TypedDict, total=False):
    status: Literal["success", "no_match", "disabled", "unavailable", "not_requested"]
    reason: str | None
    tenant_id: str | None
    source: str
    read_at: str
    accounts: list[str]
    limit: int
    requested_as_of: str | None
    as_of: str | None
    cache: dict[str, Any]
    http_status: int | None
    graph_source_status: str | None
    graph_source_reason: str | None
    received_count: int
    valid_count: int
    adopted_count: int
    candidate_count: int
    eligible_count: int
    truncated_count: int
    excluded_after_cutoff: int
    excluded_unverifiable_import: int
    import_timestamp_missing: int
    without_timestamp: int
    adopted_without_timestamp: int
    import_cutoff_only: bool
    business_history_verified: bool
    identities: list[dict[str, Any]]
    budget: dict[str, Any]
    prompt_block: str
    prompt_sha256: str


def make_read(tenant_id: str | None, *, accounts: Sequence[str] = (), limit: int = MAX_IDENTITIES_IN_PROMPT,
              as_of: datetime | None = None,
              status: Literal["success", "no_match", "disabled", "unavailable", "not_requested"] = "not_requested",
              reason: str | None = None) -> IdentityContextRead:
    result = {"status": status, "reason": reason, "tenant_id": tenant_id, "source": _SOURCE,
              "read_at": _stamp(as_of) or _now().isoformat(), "accounts": list(accounts), "limit": limit,
              "requested_as_of": _stamp(as_of), "as_of": None,
              "cache": {"source": "none", "freshness": "not_available", "age_seconds": None, "ttl_seconds": _CACHE_TTL_S},
              "http_status": None, "graph_source_status": None, "graph_source_reason": None,
              "received_count": 0, "valid_count": 0, "adopted_count": 0, "adopted_without_timestamp": 0,
              "import_cutoff_only": True, "business_history_verified": False, "identities": [],
              "budget": {"max_prompt_chars": _MAX_PROMPT_CHARS, "field_limits": dict(_DISPLAY_LIMITS),
                         "max_identities": MAX_IDENTITIES_IN_PROMPT, "dropped_for_limit": 0, "dropped_for_budget": 0},
              "prompt_block": "", "prompt_sha256": _sha("")}
    result.update({key: 0 for key in _COUNTS})
    return result


@dataclass(frozen=True)
class IdentityContext:
    identities: tuple[Mapping[str, Any], ...] = ()
    as_of: str | None = None
    excluded_after_cutoff: int = 0
    # The API counts every returned row as business-history unknown, even
    # when its Employee import timestamp is native and precedes the split.
    without_timestamp: int = 0
    read: IdentityContextRead = field(default_factory=dict)
    budget: dict[str, Any] = field(default_factory=dict)
    prompt_block: str = ""

    def as_state(self) -> dict[str, Any]:
        return {"identities": deepcopy(list(self.identities)), "as_of": self.as_of,
                "excluded_after_cutoff": self.excluded_after_cutoff, "without_timestamp": self.without_timestamp,
                "adopted_without_timestamp": len(self.identities), "import_cutoff_only": True,
                "business_history_verified": False, "budget": deepcopy(self.budget),
                "prompt_block": self.prompt_block, "prompt_sha256": _sha(self.prompt_block)}

    def as_read(self) -> IdentityContextRead:
        read = deepcopy(self.read) if self.read else make_read(None, status="success" if self.identities else "no_match")
        read.update(self.as_state())
        read["adopted_count"] = len(self.identities)
        read["adopted_identity_ids"] = [row.get("identity_id") for row in self.identities]
        return read

    def __bool__(self) -> bool:
        return bool(self.identities)


def accounts_for(raw_alert: Mapping[str, Any] | None) -> list[str]:
    """Principals only; a hostname belongs to the asset dimension."""
    raw = raw_alert or {}
    out: list[str] = []
    for key in ("username", "user", "user_name", "src_user", "actor", "principal"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            out.append(value.strip())
    values = raw.get("affected_users")
    if isinstance(values, list):
        out.extend(value.strip() for value in values if isinstance(value, str) and value.strip())
    return sorted({value.lower() for value in out})[:MAX_IDENTITIES_IN_PROMPT]


def _count(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("invalid identity count")
    return value


def _row_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(row.get(key) for key in ("identity_id", "employee_id", "department_id", "manager_id"))


def _validate_row(row: Any, *, tenant_id: str, accounts: Sequence[str], as_of: datetime | None) -> None:
    if not isinstance(row, dict) or not set(_SOURCE_FIELDS).issubset(row):
        raise ValueError("invalid identity row shape")
    for stem in ("identity", "employee", "department", "manager"):
        identity, kind = row[stem + "_id"], row[stem + "_id_kind"]
        if identity is None:
            if kind is not None or stem == "identity":
                raise ValueError("identity ID/kind mismatch")
        elif not isinstance(identity, str) or not identity.strip() or kind not in {"business_id", "element_id"}:
            raise ValueError("invalid identity node reference")
    for key in ("account", "provider", "employee", "title", "employment_type", "start_date", "end_date",
                "department", "manager", "manager_email"):
        value = row[key]
        if value is not None and not isinstance(value, str):
            raise ValueError("invalid identity display field")
        if isinstance(value, str):
            value.encode("utf-8")
    if not row["account"] or row["account"].lower() not in accounts:
        raise ValueError("identity row does not match requested account")
    if row["is_active"] is not None and not isinstance(row["is_active"], bool):
        raise ValueError("invalid directory active flag")
    if not isinstance(row["employee_linked"], bool) or row["employee_linked"] != (row["employee_id"] is not None):
        raise ValueError("invalid employee link flag")
    relations = row["relationship_source"]
    expected = {"employee_identity": "AUTHENTICATES_AS" if row["employee_id"] else None,
                "employee_department": "BELONGS_TO" if row["department_id"] else None,
                "manager_employee": "MANAGES" if row["manager_id"] else None}
    if relations != expected:
        raise ValueError("identity relationship provenance differs")
    if row["employee_id"] is None and any(row[key] is not None for key in (
            "employee", "title", "is_active", "employment_type", "start_date", "end_date", "department_id",
            "manager_id", "department", "manager", "manager_email")):
        raise ValueError("employee fields without a linked employee")
    if row["department_id"] is None and row["department"] is not None:
        raise ValueError("department fields without a department")
    if row["manager_id"] is None and any(row[key] is not None for key in ("manager", "manager_email")):
        raise ValueError("manager fields without a manager")
    stamp_status = row["imported_at_status"]
    if stamp_status not in {"native", "missing", "unsupported"}:
        raise ValueError("invalid import timestamp status")
    if stamp_status == "native":
        stamp = _date(row["imported_at"])
        if as_of is not None and stamp > _date(_stamp(as_of)):
            raise LookupError("identity import postdates split")
    elif row["imported_at"] is not None:
        raise ValueError("unverified import timestamp must not be exposed as a date")
    if as_of is not None and stamp_status != "native":
        raise LookupError("unverifiable import timestamp")
    if not isinstance(row["imported_at_raw_sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", row["imported_at_raw_sha256"]) is None:
        raise ValueError("invalid raw timestamp fingerprint")
    if row.get("row_source_sha256") != _source_hash(tenant_id, row):
        raise ValueError("identity source projection fingerprint differs")


def _validate(payload: Any, *, tenant_id: str, accounts: Sequence[str], limit: int,
              as_of: datetime | None, unavailable: bool = False) -> None:
    if (not isinstance(payload, dict) or payload.get("tenant_id") != tenant_id or payload.get("accounts") != list(accounts)
            or type(payload.get("limit")) is not int or payload.get("limit") != limit):
        raise ValueError("identity response scope/query echo differs")
    if not isinstance(payload.get("identities"), list):
        raise ValueError("invalid identity list")
    if "as_of" not in payload or (as_of is not None and payload["as_of"] is None):
        raise LookupError("identity cutoff echo missing") if as_of is not None else ValueError("missing identity cutoff echo")
    if as_of is None:
        if payload["as_of"] is not None:
            raise ValueError("unexpected identity cutoff")
    else:
        try:
            if _date(payload["as_of"]) != _date(_stamp(as_of)):
                raise LookupError("identity cutoff echo differs")
        except (TypeError, ValueError) as error:
            raise LookupError("identity cutoff echo invalid") from error
    for key in _COUNTS:
        _count(payload.get(key))
    rows = payload["identities"]
    if len(rows) > limit or payload["without_timestamp"] != len(rows):
        raise ValueError("identity rows/count disagree")
    if payload["candidate_count"] != payload["eligible_count"] + payload["excluded_after_cutoff"] + payload["excluded_unverifiable_import"]:
        raise ValueError("identity candidate counts disagree")
    if payload["eligible_count"] != len(rows) + payload["truncated_count"] or payload["import_timestamp_missing"] > payload["candidate_count"]:
        raise ValueError("identity eligibility counts disagree")
    if as_of is None and (payload["excluded_after_cutoff"] or payload["excluded_unverifiable_import"]):
        raise ValueError("unrequested identity cutoff excluded rows")
    if unavailable:
        if payload.get("source_status") != "unavailable" or payload.get("source_reason") not in _GRAPH_FAILURE_REASONS:
            raise ValueError("invalid graph failure body")
        if rows or any(payload[key] for key in _COUNTS):
            raise ValueError("failed graph read carries material")
        return
    if payload.get("source_status") != ("success" if rows else "no_match") or payload.get("source_reason") is not None:
        raise ValueError("invalid graph success state")
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        _validate_row(row, tenant_id=tenant_id, accounts=accounts, as_of=as_of)
        key = _row_key(row)
        if key in seen:
            raise ValueError("duplicate identity path")
        seen.add(key)
    if sum(row["imported_at_status"] == "missing" for row in rows) > payload["import_timestamp_missing"]:
        raise ValueError("missing import timestamp count differs")


def _failure(read: IdentityContextRead, reason: str, payload: Any = None) -> IdentityContext:
    facts = deepcopy(read)
    facts.update(status="unavailable", reason=reason, valid_count=0, adopted_count=0, adopted_without_timestamp=0,
                 identities=[], prompt_block="", prompt_sha256=_sha(""))
    if isinstance(payload, Mapping):
        facts["as_of"] = payload.get("as_of") if isinstance(payload.get("as_of"), str) else None
        rows = payload.get("identities")
        facts["received_count"] = len(rows) if isinstance(rows, list) else 0
        for key in _COUNTS:
            value = payload.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                facts[key] = value
    return IdentityContext(as_of=facts.get("as_of"), excluded_after_cutoff=facts.get("excluded_after_cutoff", 0),
                           without_timestamp=facts.get("without_timestamp", 0), read=facts, budget=deepcopy(facts["budget"]))


async def fetch_identity_context(tenant_id: str | None, *, accounts: Sequence[str], as_of: datetime | None = None,
                                 limit: int = MAX_IDENTITIES_IN_PROMPT) -> IdentityContext:
    """Read tenant-authorized graph material, preserving failure/source facts."""
    valid_names = isinstance(accounts, Sequence) and not isinstance(accounts, (str, bytes)) and all(isinstance(name, str) for name in accounts)
    names = sorted({name.strip().lower() for name in accounts if name.strip()}) if valid_names else []
    if as_of is not None and not isinstance(as_of, datetime):
        return _failure(make_read(tenant_id, accounts=names, limit=limit), "invalid_request")
    read = make_read(tenant_id, accounts=names, limit=limit, as_of=as_of)
    if not enabled():
        read.update(status="disabled")
        return IdentityContext(read=read, budget=deepcopy(read["budget"]))
    if not tenant_id:
        return _failure(read, "missing_tenant")
    if not valid_names or len(names) > 25 or isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 25:
        return _failure(read, "invalid_request")
    if not names:
        read.update(reason="empty_accounts")
        return IdentityContext(read=read, budget=deepcopy(read["budget"]))
    token = _credential(tenant_id, keys_file_env="AISOC_TRIAGE_IDENTITY_KEYS_FILE")
    if not token:
        return _failure(read, "not_configured")
    url = f"{_API_URL.rstrip('/')}/api/v1/graph/identity-context"
    key = (tenant_id, url, _sha(token), tuple(names), limit, _stamp(as_of))
    cached = _cache.get(key)
    clock = time.monotonic()
    age = max(0.0, clock - cached[0]) if cached else None
    read["cache"] = {"source": "none", "freshness": "expired" if cached else "not_available", "age_seconds": age, "ttl_seconds": _CACHE_TTL_S}
    if cached is not None and age is not None and age < _CACHE_TTL_S:
        try:
            _validate(cached[2], tenant_id=tenant_id, accounts=names, limit=limit, as_of=as_of)
        except LookupError:
            _cache.pop(key, None)
            return _failure(read, "cutoff_not_honoured", cached[2])
        except (ValueError, TypeError, AttributeError, OverflowError):
            _cache.pop(key, None)
            return _failure(read, "invalid_response", cached[2])
        read.update(http_status=200, graph_source_status=cached[2]["source_status"], graph_source_reason=None)
        read["cache"].update(source="memory", freshness="fresh", fetched_at=cached[1])
        return _shape(cached[2], limit=limit, read=read)
    _cache.pop(key, None)
    params = [("tenant_id", tenant_id), ("limit", str(limit))] + [("accounts", name) for name in names]
    if as_of is not None:
        params.append(("as_of", _stamp(as_of)))
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            response = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError:
        logger.warning("triage_identity.unreachable")
        return _failure(read, "transport_error")
    read["http_status"] = response.status_code
    payload = None
    if response.status_code != 200:
        if response.status_code == 503:
            try:
                payload = response.json()
                _validate(payload, tenant_id=tenant_id, accounts=names, limit=limit, as_of=as_of, unavailable=True)
                read.update(graph_source_status=payload["source_status"], graph_source_reason=payload["source_reason"])
            except (ValueError, TypeError, AttributeError, LookupError, OverflowError):
                payload = None
        return _failure(read, "auth_failed" if response.status_code in {401, 403} else "http_error", payload)
    try:
        payload = response.json()
        _validate(payload, tenant_id=tenant_id, accounts=names, limit=limit, as_of=as_of)
    except LookupError:
        return _failure(read, "cutoff_not_honoured", payload)
    except (ValueError, TypeError, AttributeError, OverflowError):
        return _failure(read, "invalid_response", payload)
    read.update(graph_source_status=payload["source_status"], graph_source_reason=None)
    fetched_at = _stamp(as_of) or _now().isoformat()
    _cache[key] = (clock, fetched_at, deepcopy(payload))
    read["cache"] = {"source": "network", "freshness": "fresh", "age_seconds": 0.0, "ttl_seconds": _CACHE_TTL_S, "fetched_at": fetched_at}
    return _shape(payload, limit=limit, read=read)


def _cap(value: str, width: int) -> str:
    marker = "…[truncated]"
    return value if len(value) <= width else value[:max(0, width - len(marker))] + marker


def _line(row: Mapping[str, Any]) -> str:
    display = row["display_fields"]
    bits: list[str] = []
    if display["provider"]:
        bits.append("provider " + display["provider"])
    for key, label in (("employee", ""), ("title", "title"), ("department", "department"), ("manager", "manager")):
        if display[key]:
            bits.append(display[key] if not label else label + " " + display[key])
    if row.get("employee_linked") is False:
        bits.append("directory identity found; no linked employee record")
    else:
        if row.get("is_active") is False:
            bits.append("NO LONGER ACTIVE in the directory" + (" (ended " + display["end_date"] + ")" if display["end_date"] else ""))
        elif row.get("is_active") is True:
            bits.append("active in the directory")
        if display["employment_type"]:
            bits.append(display["employment_type"])
    return "- " + display["account"] + ": " + (", ".join(bits) if bits else "directory fields not provided")


def _adopt(rows: list[Mapping[str, Any]], *, limit: int) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    candidates = rows[:min(max(1, limit), MAX_IDENTITIES_IN_PROMPT)]
    adopted: list[dict[str, Any]] = []
    empty_accounts = 0
    used = len(_HEADER) + len(_ADVISORY)
    for original in candidates:
        row = deepcopy(dict(original))
        display, raw_hashes, display_hashes, truncated = {}, {}, {}, []
        for key, width in _DISPLAY_LIMITS.items():
            value = str(row.get(key) or "")
            clean = sanitize_text(value, max_len=0)
            display[key] = _cap(clean, width)
            raw_hashes[key] = _sha(value)
            display_hashes[key] = _sha(display[key])
            if display[key] != clean:
                truncated.append(key)
        if not display["account"]:
            empty_accounts += 1
            continue
        row.update(display_fields=display, raw_field_sha256=raw_hashes, adopted_field_sha256=display_hashes,
                   truncated_fields=truncated, business_history_verified=False)
        text = _line(row)
        if used + (1 if adopted else 0) + len(text) > _MAX_PROMPT_CHARS:
            break
        row.update(rendered_text=text, rendered_sha256=_sha(text))
        adopted.append(row)
        used += (1 if len(adopted) > 1 else 0) + len(text)
    block = _HEADER + "\n".join(row["rendered_text"] for row in adopted) + _ADVISORY if adopted else ""
    assert len(block) <= _MAX_PROMPT_CHARS
    return adopted, block, {"max_prompt_chars": _MAX_PROMPT_CHARS, "field_limits": dict(_DISPLAY_LIMITS),
                            "max_identities": MAX_IDENTITIES_IN_PROMPT, "dropped_for_limit": len(rows) - len(candidates),
                            "dropped_for_budget": len(candidates) - len(adopted) - empty_accounts,
                            "dropped_for_empty_account": empty_accounts, "prompt_chars": len(block),
                            "truncated_fields": sum(len(row["truncated_fields"]) for row in adopted)}


def _shape(payload: Mapping[str, Any], *, limit: int, read: IdentityContextRead | None = None) -> IdentityContext:
    rows = payload.get("identities")
    rows = [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []
    adopted, block, budget = _adopt(rows, limit=limit)
    facts = deepcopy(read) if read is not None else make_read(payload.get("tenant_id"), accounts=payload.get("accounts") or [], limit=limit)
    facts.update(status="success" if rows else "no_match", received_count=len(rows), valid_count=len(rows),
                 graph_source_status=payload.get("source_status", "success" if rows else "no_match"),
                 graph_source_reason=payload.get("source_reason"))
    for key in _COUNTS:
        facts[key] = int(payload.get(key) or 0)
    facts["identity_only_count"] = sum(row.get("employee_linked") is False for row in rows)
    facts["missing_import_count_returned"] = sum(row.get("imported_at_status") == "missing" for row in rows)
    accounts = [str(row.get("account") or "").lower() for row in rows]
    facts["ambiguous_account_count"] = len({account for account in accounts if accounts.count(account) > 1})
    echo = str(payload["as_of"]) if payload.get("as_of") else None
    return IdentityContext(identities=tuple(adopted), as_of=echo,
                           excluded_after_cutoff=int(payload.get("excluded_after_cutoff") or 0),
                           without_timestamp=int(payload.get("without_timestamp") or 0), read=facts, budget=budget, prompt_block=block)


def enforce_cutoff(found: IdentityContext, *, tenant_id: str | None, accounts: Sequence[str], as_of: datetime) -> IdentityContext:
    facts = found.as_read()
    if facts.get("tenant_id") != tenant_id:
        return _failure(facts, "invalid_response")
    names = sorted({name.strip().lower() for name in accounts if name.strip()})
    facts.update(accounts=names, requested_as_of=_stamp(as_of), read_at=_stamp(as_of), import_cutoff_only=True)
    facts["cache"] = {**facts.get("cache", {}), "source": "cutoff", "freshness": "frozen", "split_at": _stamp(as_of)}
    if facts.get("status") not in {"success", "no_match"}:
        return replace(found, identities=(), prompt_block="", read=facts)
    try:
        if _date(found.as_of) != _date(_stamp(as_of)):
            return _failure(facts, "cutoff_not_honoured")
    except (ValueError, TypeError, AttributeError, OverflowError):
        return _failure(facts, "cutoff_not_honoured")
    try:
        if found.without_timestamp != facts.get("received_count"):
            return _failure(facts, "invalid_response")
        for row in found.identities:
            _validate_row(dict(row), tenant_id=tenant_id, accounts=names, as_of=as_of)
    except LookupError:
        return _failure(facts, "cutoff_not_honoured")
    except (ValueError, TypeError, AttributeError, OverflowError):
        return _failure(facts, "invalid_response")
    return replace(found, read=facts)


def render_for_prompt(state_value: Mapping[str, Any] | None) -> str:
    if not state_value:
        return ""
    if isinstance(state_value.get("prompt_block"), str):
        return state_value["prompt_block"]
    rows = state_value.get("identities")
    return _adopt([row for row in rows if isinstance(row, Mapping)], limit=MAX_IDENTITIES_IN_PROMPT)[1] if isinstance(rows, list) else ""


def render_read_status(read: Mapping[str, Any]) -> str:
    status = read.get("status", "not_requested")
    if status == "not_requested":
        return ""
    text = (f"Directory context read: status={status}; freshness={(read.get('cache') or {}).get('freshness', 'not_available')}; "
            f"source={read.get('source') or _SOURCE}; import_cutoff_only; business history unverified.")
    if read.get("reason"):
        text += f" Reason={read['reason']}."
    if read.get("graph_source_status"):
        text += f" Graph source={read['graph_source_status']}"
        if read.get("graph_source_reason"):
            text += "; reason=" + str(read["graph_source_reason"])
        text += "."
    if status in {"disabled", "unavailable"}:
        text += " No directory material was adopted; this does not establish that the account is unknown or abnormal."
    elif status == "no_match":
        text += " No permitted paths matched these accounts; this is not a claim about all directory records."
    return text


def basis(state_value: Mapping[str, Any] | None) -> list[str]:
    rows = (state_value or {}).get("identities")
    rows = [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []
    if not rows:
        return []
    inactive = sum(row.get("is_active") is False for row in rows)
    line = f"Directory context in prompt: {len(rows)} principal(s)"
    if inactive:
        line += f", {inactive} no longer active in the directory"
    return [line]
