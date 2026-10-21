"""The last few times an analyst decided an alert of this shape, and why.

Gap-closure Phase 6.3, agents half.

What this adds that organisation memory does not
------------------------------------------------
``app/context/organisation_memory.py`` already reads compiled statements, and
compiling is the point of that module: a reason has to recur across
independent analysts before it becomes a durable claim about the estate. That
threshold is deliberate and should not be lowered.

It also means a disagreement recorded once is invisible there. An analyst
looking at the queue by hand sees the last three times this rule fired and
what a colleague did about it, whether or not any of it has crossed a
corroboration threshold, and that is what this reads: the raw decisions, in
order, with the reason each analyst gave.

The application appends one ``aisoc_analyst_feedback`` row per tagged
disagreement. The table has no immutable-history constraint, so this reads the
current rows and a creation-time cutoff cannot reconstruct later edits. It
can answer "the last N" at all. The override row in institutional memory
cannot: it is upserted per signature, so it holds the latest decision and no
history.

Matching
--------
A decision reaches an alert two ways, and the stronger one is ordered first.
A decision tagged against the same **rule** is the most specific claim
available. A decision whose scope value is one of the alert's own entities (a
host, a principal) is the fallback that lets a decision about one machine be
seen from a different rule.

How the text is contained
-------------------------
First-party, like organisation memory and unlike a knowledge-base article: a
disposition and a reason code come from a closed vocabulary the server owns,
and the free-text note is typed by an authenticated analyst in the console.
So it is sanitised and capped rather than nonce-fenced. The cap matters
regardless of trust, because the note interpolates nothing but is unbounded
in length, and the prompt budget is shared with the evidence.

The wording is advisory for a reason specific to this source. These are
individual opinions, some of which have not been corroborated by anybody, and
a prompt that presented them as facts would let one analyst's mistaken
closure steer every later alert of that shape.

Point in time
-------------
A ``CUTOFF`` source, like runbooks: this is a per-alert query against a table
that grows with every decision a SOC makes, so the freeze is an ``as_of`` the
frozen reader supplies and the server applies, and the server reports how many
rows it refused.

This is the leakiest of the three sources by construction. A decision recorded
during the test window is literally an analyst's answer to an alert in that
window, so a replay that could see them would be grading the agent on the
labels it is about to be marked against. Phase 1's outcome-prior leak by a
shorter route.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
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

__all__ = [
    "MAX_DISPOSITIONS_IN_PROMPT",
    "RecentDispositions",
    "clear_cache",
    "enabled",
    "entities_for",
    "fetch_recent_dispositions",
    "render_for_prompt",
    "RecentDispositionsRead",
    "make_read",
    "render_read_status",
    "enforce_cutoff",
]

_API_URL = os.getenv("API_SERVICE_URL", "http://api:8000")
_TIMEOUT_S = float(os.getenv("AISOC_TRIAGE_DISPOSITIONS_TIMEOUT_S", "5"))

#: Decisions placed in one prompt. Five is "what did we do the last few
#: times"; fifty is a different product, and it is the evidence's budget.
MAX_DISPOSITIONS_IN_PROMPT = int(os.getenv("AISOC_TRIAGE_DISPOSITIONS_TOP_N", "5"))

#: Per-note cap. The note is free text an analyst typed with no length limit.
_MAX_NOTE_CHARS = 240

_CACHE_TTL_S = float(os.getenv("AISOC_TRIAGE_DISPOSITIONS_TTL_S", "120"))

_cache: dict[tuple[Any, ...], tuple[float, str, dict[str, Any]]] = {}
_SOURCE = "api.feedback.recent-dispositions"
_MAX_PROMPT_CHARS = 3000
_TRUNCATED = "…[truncated]"
_HEADER = "Recent analyst decisions on alerts of this shape in this tenant, newest first:\n"
_ADVISORY = (
    "\nThese are individual decisions, not compiled organisation memory: some have not "
    "been corroborated by a second analyst, and any of them may have been wrong. Treat a "
    "repeated benign decision as a reason to consider benign_true_positive and to say which "
    "decision you are following. It never overrides direct evidence of compromise in this "
    "alert's own telemetry, and a single decision is one person's opinion."
)
# Fixed-upstream REASON_CODES labels; no new vocabulary or inference is added.
_REASON_LABELS = {
    "known_admin_tool": "Known administrative tool", "approved_pentest": "Approved penetration test",
    "expected_service_account": "Expected service-account behaviour", "known_scanner": "Known vulnerability scanner",
    "business_application": "Sanctioned business application", "bad_detection_logic": "Bad detection logic",
    "missing_context": "Missing context", "true_positive_confirmed": "Confirmed true positive",
}
# Mirror the fixed upstream closed vocabulary. Importing app.agents here
# executes that package's __init__, which imports auto_triage_agent back
# into this reader before it has finished defining basis/render functions.
# The fresh-process tests also compare this mirror to the canonical module.
_AI_VERDICTS = frozenset({"true_positive", "benign_true_positive", "false_positive", "benign", "needs_review", "escalate"})
_ANALYST_VERDICTS = _AI_VERDICTS - {"needs_review"}
_SOURCE_FIELDS = (
    "feedback_id", "created_at", "decided_at", "analyst_disposition", "ai_disposition", "reason_code",
    "reason_label", "note", "scope", "scope_value", "rule_id", "by_rule", "by_entity",
)



def enabled() -> bool:
    return os.getenv("AISOC_TRIAGE_DISPOSITIONS_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}


def clear_cache() -> None:
    """Drop cached decisions. Tests, and the feedback path."""
    _cache.clear()


class RecentDispositionsRead(TypedDict, total=False):
    status: Literal["success", "no_match", "disabled", "unavailable", "not_requested"]
    reason: str | None
    tenant_id: str | None
    source: str
    read_at: str
    rule_id: str
    entities: list[str]
    limit: int
    requested_as_of: str | None
    as_of: str | None
    cache: dict[str, Any]
    http_status: int | None
    received_count: int
    valid_count: int
    adopted_count: int
    excluded_after_cutoff: int
    without_timestamp: int
    decisions: list[dict[str, Any]]
    feedback_ids: list[str]
    budget: dict[str, Any]
    prompt_block: str
    prompt_sha256: str


def _now() -> datetime:
    return datetime.now(UTC)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_hash(tenant_id: str, row: Mapping[str, Any]) -> str:
    value = {"tenant_id": tenant_id, **{key: row[key] for key in _SOURCE_FIELDS}}
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def _stamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (value.replace(tzinfo=UTC) if value.tzinfo is None else value).astimezone(UTC).isoformat()


def _date(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("invalid disposition timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None or result.utcoffset().total_seconds() != 0:
        raise ValueError("disposition timestamps must be UTC")
    return result


def make_read(
    tenant_id: str | None, *, rule_id: str = "", entities: Sequence[str] = (), limit: int = MAX_DISPOSITIONS_IN_PROMPT,
    as_of: datetime | None = None,
    status: Literal["success", "no_match", "disabled", "unavailable", "not_requested"] = "not_requested",
    reason: str | None = None,
) -> RecentDispositionsRead:
    return {
        "status": status, "reason": reason, "tenant_id": tenant_id, "source": _SOURCE,
        "read_at": _stamp(as_of) or _now().isoformat(), "rule_id": rule_id, "entities": list(entities), "limit": limit,
        "requested_as_of": _stamp(as_of), "as_of": None,
        "cache": {"source": "none", "freshness": "not_available", "age_seconds": None, "ttl_seconds": _CACHE_TTL_S},
        "http_status": None, "received_count": 0, "valid_count": 0, "adopted_count": 0,
        "excluded_after_cutoff": 0, "without_timestamp": 0, "decisions": [], "feedback_ids": [],
        "budget": {"max_prompt_chars": _MAX_PROMPT_CHARS, "max_note_chars": _MAX_NOTE_CHARS,
                   "max_decisions": MAX_DISPOSITIONS_IN_PROMPT, "dropped_for_limit": 0, "dropped_for_budget": 0},
        "prompt_block": "", "prompt_sha256": _sha(""),
    }


@dataclass(frozen=True)
class RecentDispositions:
    """Compatibility projection with explicit read and literal-adoption facts."""

    decisions: tuple[Mapping[str, Any], ...] = ()
    as_of: str | None = None
    excluded_after_cutoff: int = 0
    without_timestamp: int = 0
    read: RecentDispositionsRead = field(default_factory=dict)
    budget: dict[str, Any] = field(default_factory=dict)
    prompt_block: str = ""

    def as_state(self) -> dict[str, Any]:
        return {"decisions": deepcopy(list(self.decisions)), "as_of": self.as_of,
                "excluded_after_cutoff": self.excluded_after_cutoff, "without_timestamp": self.without_timestamp,
                "budget": deepcopy(self.budget), "prompt_block": self.prompt_block,
                "prompt_sha256": _sha(self.prompt_block)}

    def as_read(self) -> RecentDispositionsRead:
        read = deepcopy(self.read) if self.read else make_read(None, status="success" if self.decisions else "no_match")
        read.update(self.as_state())
        read["adopted_count"] = len(self.decisions)
        read["feedback_ids"] = [row.get("feedback_id") for row in self.decisions if row.get("feedback_id")]
        return read

    def __bool__(self) -> bool:
        return bool(self.decisions)


def entities_for(raw_alert: Mapping[str, Any] | None) -> list[str]:
    """The entity values a past decision could have been scoped to.

    Host and principal only. An IP is an entity a decision can be scoped to in
    principle, and matching on one here would pull in every decision about a
    NAT gateway or a shared egress address, which is a suppression nobody
    wrote.
    """
    raw = raw_alert or {}
    out: list[str] = []
    for key in ("hostname", "host", "username", "user", "user_name", "src_user"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            out.append(value.strip())
    for key in ("affected_hosts", "affected_users"):
        values = raw.get(key)
        if isinstance(values, list):
            out.extend(v.strip() for v in values if isinstance(v, str) and v.strip())
    return sorted({v.lower() for v in out})[:10]


def _count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("invalid disposition count")
    return value


def _matching(row: Mapping[str, Any], rule_id: str, entities: Sequence[str]) -> bool:
    by_rule = bool(rule_id and row.get("rule_id") == rule_id)
    scope_value = row.get("scope_value")
    by_entity = bool(isinstance(scope_value, str) and scope_value and scope_value.lower() in entities)
    return (isinstance(row.get("by_rule"), bool) and isinstance(row.get("by_entity"), bool)
            and row["by_rule"] == by_rule and row["by_entity"] == by_entity and (by_rule or by_entity))


def _validate(payload: Any, *, tenant_id: str, rule_id: str, entities: Sequence[str], as_of: datetime | None, limit: int) -> None:
    if not isinstance(payload, dict) or payload.get("tenant_id") != tenant_id or not isinstance(payload.get("dispositions"), list):
        raise ValueError("invalid dispositions response tenant or shape")
    if "as_of" not in payload:
        if as_of is not None:
            raise LookupError("missing disposition cutoff echo")
        raise ValueError("missing disposition cutoff echo")
    echo = payload["as_of"]
    if as_of is None:
        if echo is not None:
            raise ValueError("unexpected disposition cutoff")
    else:
        try:
            if echo is None or _date(echo) != _date(_stamp(as_of)):
                raise LookupError("disposition cutoff not honoured")
        except (ValueError, TypeError) as exc:
            raise LookupError("disposition cutoff not provable") from exc
    _count(payload.get("excluded_after_cutoff")); _count(payload.get("without_timestamp"))
    rows = payload["dispositions"]
    if len(rows) > limit:
        raise ValueError("disposition rows exceed requested limit")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid disposition row")
        if not set(_SOURCE_FIELDS).issubset(row):
            raise ValueError("missing disposition source fields")
        identity = str(uuid.UUID(row.get("feedback_id")))
        if identity in seen:
            raise ValueError("duplicate disposition ID")
        seen.add(identity)
        if row.get("analyst_disposition") not in _ANALYST_VERDICTS or row.get("ai_disposition") not in _AI_VERDICTS:
            raise ValueError("invalid disposition vocabulary")
        if row.get("reason_code") not in _REASON_LABELS or row.get("reason_label") != _REASON_LABELS[row["reason_code"]]:
            raise ValueError("invalid disposition reason")
        if row.get("scope") not in {"rule", "entity", "binary", "tenant"}:
            raise ValueError("invalid disposition scope")
        for key in ("note", "scope_value"):
            if not isinstance(row.get(key), str):
                raise ValueError("invalid disposition text")
            row[key].encode("utf-8")
        if row.get("rule_id") is not None and not isinstance(row["rule_id"], str):
            raise ValueError("invalid disposition rule")
        if not _matching(row, rule_id, entities):
            raise ValueError("invalid disposition matching basis")
        created, decided = _date(row.get("created_at")), _date(row.get("decided_at"))
        if created != decided:
            raise ValueError("disposition timestamp aliases disagree")
        if as_of is not None and created > _date(_stamp(as_of)):
            raise LookupError("disposition row postdates cutoff")
        if row.get("row_source_sha256") != _source_hash(tenant_id, row):
            raise ValueError("disposition source fingerprint differs")


def _failure(read: RecentDispositionsRead, reason: str, payload: Any = None) -> RecentDispositions:
    facts = deepcopy(read)
    facts.update(status="unavailable", reason=reason, valid_count=0, adopted_count=0, decisions=[], feedback_ids=[],
                 prompt_block="", prompt_sha256=_sha(""))
    if isinstance(payload, Mapping):
        facts["as_of"] = payload.get("as_of") if isinstance(payload.get("as_of"), str) else None
        rows = payload.get("dispositions")
        facts["received_count"] = len(rows) if isinstance(rows, list) else 0
        for key in ("excluded_after_cutoff", "without_timestamp"):
            value = payload.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                facts[key] = value
    return RecentDispositions(as_of=facts.get("as_of"), excluded_after_cutoff=facts.get("excluded_after_cutoff", 0),
                              without_timestamp=facts.get("without_timestamp", 0), read=facts,
                              budget=deepcopy(facts["budget"]))


async def fetch_recent_dispositions(
    tenant_id: str | None, *, rule_id: str = "", entities: Sequence[str] = (), as_of: datetime | None = None,
    limit: int = MAX_DISPOSITIONS_IN_PROMPT,
) -> RecentDispositions:
    """Tenant-authorised current decisions; no failed read adopts old material."""
    rule = rule_id.strip() if isinstance(rule_id, str) else ""
    valid_entities = isinstance(entities, Sequence) and not isinstance(entities, (str, bytes)) and all(isinstance(value, str) for value in entities)
    entity_list = sorted({value.strip().lower() for value in entities if value.strip()}) if valid_entities else []
    if as_of is not None and not isinstance(as_of, datetime):
        return _failure(make_read(tenant_id, rule_id=rule, entities=entity_list, limit=limit), "invalid_request")
    read = make_read(tenant_id, rule_id=rule, entities=entity_list, limit=limit, as_of=as_of)
    if not enabled():
        read.update(status="disabled")
        return RecentDispositions(read=read, budget=deepcopy(read["budget"]))
    if not tenant_id:
        return _failure(read, "missing_tenant")
    if not valid_entities or not isinstance(rule_id, str) or isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        return _failure(read, "invalid_request")
    if not rule and not entity_list:
        read.update(reason="empty_match")
        return RecentDispositions(read=read, budget=deepcopy(read["budget"]))
    token = _credential(tenant_id, keys_file_env="AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE")
    if not token:
        logger.warning("triage_dispositions.not_configured")
        return _failure(read, "not_configured")
    url = f"{_API_URL.rstrip('/')}/api/v1/feedback/recent-dispositions"
    key = (tenant_id, url, _sha(token), rule, tuple(entity_list), _stamp(as_of), limit)
    cached = _cache.get(key)
    clock = time.monotonic()
    age = max(0.0, clock - cached[0]) if cached else None
    read["cache"] = {"source": "none", "freshness": "expired" if cached else "not_available", "age_seconds": age, "ttl_seconds": _CACHE_TTL_S}
    if cached is not None and age is not None and age < _CACHE_TTL_S:
        try:
            _validate(cached[2], tenant_id=tenant_id, rule_id=rule, entities=entity_list, as_of=as_of, limit=limit)
        except LookupError:
            _cache.pop(key, None)
            return _failure(read, "cutoff_not_honoured", cached[2])
        except (ValueError, TypeError, AttributeError, OverflowError):
            _cache.pop(key, None)
            return _failure(read, "invalid_response", cached[2])
        read.update(http_status=200)
        read["cache"].update(source="memory", freshness="fresh", fetched_at=cached[1])
        return _shape(cached[2], limit=limit, read=read)
    # Once a refresh is required, a failed refresh must not leave an old
    # entry available for a subsequent adoption (including a TTL change).
    _cache.pop(key, None)
    params: list[tuple[str, str]] = [("tenant_id", tenant_id), ("rule_id", rule), ("limit", str(limit))]
    params.extend(("entities", entity) for entity in entity_list)
    if as_of is not None:
        params.append(("as_of", _stamp(as_of)))
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            response = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError:
        logger.warning("triage_dispositions.unreachable")
        return _failure(read, "transport_error")
    read["http_status"] = response.status_code
    if response.status_code != 200:
        logger.warning("triage_dispositions.refused", status_code=response.status_code)
        return _failure(read, "auth_failed" if response.status_code in {401, 403} else "http_error")
    payload = None
    try:
        payload = response.json()
        _validate(payload, tenant_id=tenant_id, rule_id=rule, entities=entity_list, as_of=as_of, limit=limit)
    except LookupError:
        return _failure(read, "cutoff_not_honoured", payload)
    except (ValueError, TypeError, AttributeError, OverflowError):
        return _failure(read, "invalid_response", payload)
    fetched_at = _stamp(as_of) or _now().isoformat()
    _cache[key] = (clock, fetched_at, deepcopy(payload))
    read["cache"] = {"source": "network", "freshness": "fresh", "age_seconds": 0.0, "ttl_seconds": _CACHE_TTL_S, "fetched_at": fetched_at}
    return _shape(payload, limit=limit, read=read)


def _cap(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[:max(0, width - len(_TRUNCATED))] + _TRUNCATED if width >= len(_TRUNCATED) else text[:width]


def _line(row: Mapping[str, Any]) -> str:
    verdict = row["analyst_disposition"]
    when = str(row.get("decided_at") or "")[:10]
    parts = [f"- {when or 'undated'}: an analyst closed this as **{verdict}**"]
    overturned = row.get("ai_disposition") or ""
    if overturned and overturned != verdict:
        parts.append(f", overturning an automated {overturned}")
    if row.get("reason_label"):
        parts.append(f". Reason: {row['reason_label']}")
    if row.get("scope_text"):
        parts.append(f" (scoped to {row['scope_text']})")
    if row.get("note"):
        parts.append(f'. Note: "{row["note"]}"')
    return "".join(parts)


def _adopt(rows: list[Mapping[str, Any]], *, limit: int) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    used = len(_HEADER) + len(_ADVISORY)
    candidates = rows[:min(max(1, limit), MAX_DISPOSITIONS_IN_PROMPT)]
    for original in candidates:
        row = deepcopy(dict(original))
        raw_note = str(row.get("note") or "")
        note = sanitize_text(raw_note, max_len=0)
        raw_scope = str(row.get("scope_value") or "")
        row.update(analyst_disposition=_cap(sanitize_text(str(row.get("analyst_disposition") or ""), max_len=0), 40),
                   ai_disposition=_cap(sanitize_text(str(row.get("ai_disposition") or ""), max_len=0), 40),
                   reason_label=_cap(sanitize_text(str(row.get("reason_label") or row.get("reason_code") or ""), max_len=0), 80),
                   scope_text=_cap(sanitize_text(raw_scope, max_len=0), 120), note=_cap(note, _MAX_NOTE_CHARS),
                   raw_note_sha256=_sha(raw_note), scope_truncated=len(raw_scope) > 120)
        if not row["analyst_disposition"]:
            continue
        separator = 1 if kept else 0
        remaining = _MAX_PROMPT_CHARS - used - separator
        if len(_line(row)) > remaining:
            base = {**row, "note": ""}
            if len(_line(base)) > remaining:
                break
            allowance = max(0, remaining - len(_line(base)) - len('. Note: ""'))
            row["note"] = _cap(row["note"], allowance) if allowance else ""
        text = _line(row)
        assert len(text) <= remaining
        row.update(note_truncated=row["note"] != note, note_sha256=_sha(row["note"]),
                   rendered_text=text, rendered_sha256=_sha(text))
        kept.append(row)
        used += separator + len(text)
    block = _HEADER + "\n".join(row["rendered_text"] for row in kept) + _ADVISORY if kept else ""
    assert len(block) <= _MAX_PROMPT_CHARS
    return kept, block, {"max_prompt_chars": _MAX_PROMPT_CHARS, "max_note_chars": _MAX_NOTE_CHARS,
                         "max_decisions": MAX_DISPOSITIONS_IN_PROMPT, "dropped_for_limit": len(rows) - len(candidates),
                         "dropped_for_budget": len(candidates) - len(kept), "prompt_chars": len(block),
                         "truncated_notes": sum(bool(row["note_truncated"]) for row in kept)}


def _shape(payload: Mapping[str, Any], *, limit: int, read: RecentDispositionsRead | None = None) -> RecentDispositions:
    """Compatibility shaping; HTTP calls validate source rows before adoption."""
    raw = payload.get("dispositions")
    rows = [row for row in raw if isinstance(row, Mapping)] if isinstance(raw, list) else []
    adopted, block, budget = _adopt(rows, limit=limit)
    facts = deepcopy(read) if read is not None else make_read(payload.get("tenant_id"), rule_id=str(payload.get("rule_id") or ""), entities=payload.get("entities") or [], limit=limit)
    echo = str(payload["as_of"]) if payload.get("as_of") else None
    facts.update(status="success" if rows else "no_match", received_count=len(rows), valid_count=len(rows), adopted_count=len(adopted), as_of=echo)
    return RecentDispositions(decisions=tuple(adopted), as_of=echo,
                              excluded_after_cutoff=int(payload.get("excluded_after_cutoff") or 0),
                              without_timestamp=int(payload.get("without_timestamp") or 0), read=facts, budget=budget, prompt_block=block)


def enforce_cutoff(found: RecentDispositions, *, tenant_id: str | None, rule_id: str, entities: Sequence[str], as_of: datetime) -> RecentDispositions:
    facts = found.as_read()
    if facts.get("tenant_id") != tenant_id:
        return _failure(facts, "invalid_response")
    normalized_entities = sorted({value.strip().lower() for value in entities if value.strip()})
    facts.update(rule_id=rule_id, entities=normalized_entities, requested_as_of=_stamp(as_of), read_at=_stamp(as_of))
    facts["cache"] = {**facts.get("cache", {}), "source": "cutoff", "freshness": "frozen", "split_at": _stamp(as_of)}
    if facts.get("status") not in {"success", "no_match"}:
        return replace(found, decisions=(), prompt_block="", read=facts)
    try:
        if _date(found.as_of) != _date(_stamp(as_of)):
            return _failure(facts, "cutoff_not_honoured")
        for row in found.decisions:
            uuid.UUID(row.get("feedback_id"))
            if _date(row.get("created_at")) != _date(row.get("decided_at")):
                return _failure(facts, "invalid_response")
            if _date(row.get("created_at")) > _date(_stamp(as_of)):
                return _failure(facts, "cutoff_not_honoured")
            if not _matching(row, rule_id, normalized_entities):
                return _failure(facts, "invalid_response")
    except (ValueError, TypeError, AttributeError):
        return _failure(facts, "cutoff_not_honoured")
    return replace(found, read=facts)


def render_for_prompt(state_value: Mapping[str, Any] | None) -> str:
    """The literal adopted block; no second sanitizer or hidden truncation."""
    if not state_value:
        return ""
    block = state_value.get("prompt_block")
    if isinstance(block, str):
        return block
    rows = state_value.get("decisions")
    rows = [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []
    return _adopt(rows, limit=MAX_DISPOSITIONS_IN_PROMPT)[1]


def render_read_status(read: Mapping[str, Any]) -> str:
    status = read.get("status", "not_requested")
    if status == "not_requested":
        return ""
    result = f"Recent analyst decisions read: status={status}; freshness={(read.get('cache') or {}).get('freshness', 'not_available')}; source={read.get('source') or _SOURCE}."
    if read.get("reason"):
        result += f" Reason={read['reason']}."
    if status in {"unavailable", "disabled"}:
        result += " No analyst-decision material was adopted; this does not establish that this tenant has no analyst history."
    elif status == "no_match":
        result += " No permitted decisions matched this rule or these entities; individual opinions are not current authorization."
    return result


def basis(state_value: Mapping[str, Any] | None) -> list[str]:
    """Confidence-basis lines naming what the prompt was given."""
    rows = (state_value or {}).get("decisions")
    rows = [r for r in rows if isinstance(r, Mapping)] if isinstance(rows, list) else []
    if not rows:
        return []
    tally: dict[str, int] = {}
    for row in rows:
        verdict = str(row.get("analyst_disposition") or "unknown")
        tally[verdict] = tally.get(verdict, 0) + 1
    summary = ", ".join(f"{count}x {verdict}" for verdict, count in sorted(tally.items()))
    return [f"Recent analyst decisions in prompt: {len(rows)} ({summary})"]
