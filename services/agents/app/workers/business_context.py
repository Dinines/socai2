"""Business-context rules in the auto-triage hot path (Phase B4).

The leading AI-SOCs win a lot of their "80% noise reduction" from
*environment-specific* rules: suppress alerts during a known maintenance
window, bump severity for production assets, route cloud alerts to the cloud
team. AiSOC has a Business Context Rules **engine + authoring UI** in
``services/api``, but it was never applied on the live path — it only ran in a
dry-run preview. This module applies it post-fusion → pre-triage.

Placement: the auto-triage worker (``fused_alert_consumer.triage``) is exactly
the post-fusion → pre-triage seam. A **suppress** rule drops the alert before
any (possibly LLM) triage spend; **severity / route / tag** rules mutate the
alert the agent then reasons over.

Why a self-contained evaluator here rather than importing the API engine: the
agents service image ships only its own ``app/`` subtree, so it can't import
``services/api``. This module re-implements the same small, documented
``when`` (dotted-path + comparators + all/any/not) / ``then``
(set_severity / route_to / tag / suppress) semantics, loads rules from a YAML
file (``AISOC_BUSINESS_CONTEXT_RULES_FILE``), and is unit-tested against those
semantics. (Unifying both call sites behind a shared package is a follow-up.)

Everything is fail-soft: a missing/invalid rules file or a bad rule degrades to
"no business context applied", never an error into triage.
"""

from __future__ import annotations

import os
import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from dataclasses import field as dc_field
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()

_ALLOWED_SEVERITIES = {"info", "low", "medium", "high", "critical"}
#: Must match ``ALLOWED_ROUTES`` in
#: ``services/api/app/services/business_context/models.py``. Duplicated rather
#: than imported because the two services ship separate images, and kept in
#: lockstep by ``tests/test_business_context_not_clause.py``. The worker used
#: to accept any string here while the console validated against this set, so
#: the two halves of the same grammar disagreed.
_ALLOWED_ROUTES = frozenset(
    {
        "tier1",
        "tier2",
        "tier3",
        "ic",
        "cloud",
        "identity",
        "appsec",
        "soc-night",
        "soc-emea",
    }
)
_ENABLED_ENV = "AISOC_BUSINESS_CONTEXT_ENABLED"
_RULES_FILE_ENV = "AISOC_BUSINESS_CONTEXT_RULES_FILE"


def policy_revision(yaml_text: str, enabled: bool) -> str:
    """Content identity, independent of process counters and read timestamps."""
    content = json.dumps({"enabled": bool(enabled), "yaml": yaml_text}, sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(content.encode()).hexdigest()


def is_enabled() -> bool:
    """Default-on; disable with AISOC_BUSINESS_CONTEXT_ENABLED=0."""
    raw = os.environ.get(_ENABLED_ENV)
    if raw is None:
        return True
    return raw.strip().lower() not in {"0", "false", "no", "off"}


# ── Rule model (faithful to services/api business_context) ────────────────────


@dataclass(frozen=True)
class RuleAction:
    set_severity: str | None = None
    route_to: str | None = None
    tag: str | None = None
    suppress: bool = False


@dataclass(frozen=True)
class RuleCondition:
    field: str | None = None
    op: str | None = None
    value: Any = None
    logical: str | None = None  # "all" | "any" | "not"
    children: tuple[RuleCondition, ...] = dc_field(default_factory=tuple)


@dataclass(frozen=True)
class BusinessContextRule:
    id: str
    when: RuleCondition
    then: RuleAction
    enabled: bool = True
    priority: int = 100


def _dotted(alert: dict[str, Any], path: str) -> Any:
    cur: Any = alert
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _cmp(op: str, actual: Any, expected: Any) -> bool:  # noqa: PLR0911
    try:
        if op == "eq":
            return actual == expected
        if op == "ne":
            return actual != expected
        if op == "lt":
            return actual < expected
        if op == "lte":
            return actual <= expected
        if op == "gt":
            return actual > expected
        if op == "gte":
            return actual >= expected
        if op == "contains":
            return expected in actual if actual is not None else False
        if op == "startswith":
            return isinstance(actual, str) and actual.startswith(str(expected))
        if op == "endswith":
            return isinstance(actual, str) and actual.endswith(str(expected))
        if op == "in":
            return actual in expected if isinstance(expected, list) else False
        if op == "not_in":
            return actual not in expected if isinstance(expected, list) else False
        if op == "exists":
            return actual is not None
        if op == "not_exists":
            return actual is None
    except TypeError:
        return False
    return False


def evaluate_condition(cond: RuleCondition, alert: dict[str, Any]) -> bool:
    if cond.logical == "all":
        return all(evaluate_condition(c, alert) for c in cond.children)
    if cond.logical == "any":
        return any(evaluate_condition(c, alert) for c in cond.children)
    if cond.logical == "not":
        return not any(evaluate_condition(c, alert) for c in cond.children)
    if cond.field and cond.op:
        return _cmp(cond.op, _dotted(alert, cond.field), cond.value)
    return False


def _parse_condition(node: Any) -> RuleCondition:
    """Parse one condition node.

    ``not`` takes a **mapping** — a single negated condition — which is what
    the console's authoring grammar accepts and validates
    (``services/api/app/services/business_context/models.py``). This parser
    used to iterate every aggregator as a list, and iterating a mapping yields
    its string keys, so ``_parse_condition("field")`` called ``.get()`` on a
    ``str`` and raised ``AttributeError``. That propagated into the caller's
    catch, which set ``rules = []`` — so one console-accepted ``not`` rule
    silently discarded the tenant's entire rule set at triage, suppressions
    included, logged at ``warning``.

    A list is still accepted for ``not`` and treated as "none of these", which
    is what the old evaluator already did with the children it never managed
    to build.
    """
    if not isinstance(node, dict):
        raise ValueError(f"condition must be a mapping, got {type(node).__name__}")

    for logical in ("all", "any"):
        if logical in node:
            kids = node[logical] or []
            if not isinstance(kids, list):
                raise ValueError(f"'{logical}' must be a list of conditions, got {type(kids).__name__}")
            return RuleCondition(logical=logical, children=tuple(_parse_condition(k) for k in kids))

    if "not" in node:
        negated = node["not"] or {}
        kids = negated if isinstance(negated, list) else [negated]
        return RuleCondition(logical="not", children=tuple(_parse_condition(k) for k in kids))

    return RuleCondition(field=node.get("field"), op=node.get("op"), value=node.get("value"))


def load_rules_from_yaml(source: str) -> list[BusinessContextRule]:
    """Parse rules YAML (single mapping or top-level ``rules:`` list).

    A rule that fails to parse is skipped and the rest are kept. It used to
    raise, and the caller's catch turned that into ``rules = []`` — so one
    malformed rule disabled every other rule the tenant had written,
    suppressions included. The blast radius of a bad rule should be that rule.
    """
    if not source or not source.strip():
        return []
    doc = yaml.safe_load(source)
    if doc is None:
        return []
    raw_rules = doc.get("rules", doc) if isinstance(doc, dict) else doc
    if isinstance(raw_rules, dict):
        raw_rules = [raw_rules]
    rules: list[BusinessContextRule] = []
    seen: set[str] = set()
    for entry in raw_rules or []:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        rid = str(entry["id"])
        if rid in seen:
            continue
        seen.add(rid)
        action = entry.get("then") or {}
        sev = action.get("set_severity")
        if sev is not None and sev not in _ALLOWED_SEVERITIES:
            sev = None
        route = action.get("route_to")
        if route is not None and route not in _ALLOWED_ROUTES:
            # The console validates this; the worker did not, so a route the
            # authoring grammar would have rejected could reach the hot path
            # if the row was written by anything else.
            logger.warning("business_context.rule_route_rejected", rule_id=rid, route_to=route)
            route = None
        try:
            when = _parse_condition(entry.get("when") or {})
        except (ValueError, AttributeError, TypeError) as exc:
            logger.warning("business_context.rule_skipped", rule_id=rid, error=str(exc))
            continue
        rules.append(
            BusinessContextRule(
                id=rid,
                when=when,
                then=RuleAction(
                    set_severity=sev,
                    route_to=route,
                    tag=action.get("tag"),
                    suppress=bool(action.get("suppress", False)),
                ),
                enabled=bool(entry.get("enabled", True)),
                priority=int(entry.get("priority", 100)),
            )
        )
    return rules


@dataclass
class BusinessContextResult:
    alert: dict[str, Any]
    matched_rule_ids: list[str]
    suppressed: bool
    severity_before: Any
    severity_after: Any
    provenance: dict[str, Any] = dc_field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return self.suppressed or bool(self.matched_rule_ids)


def apply_rules(alert: dict[str, Any], rules: list[BusinessContextRule]) -> BusinessContextResult:
    """Apply enabled rules (priority order) to a copy of ``alert``.

    Suppress short-circuits (once suppressed, downstream rules can't un-suppress),
    matching the API engine's deterministic contract.
    """
    out = dict(alert)
    severity_before = out.get("severity")
    matched: list[str] = []
    for rule in sorted((r for r in rules if r.enabled), key=lambda r: (r.priority, r.id)):
        if not evaluate_condition(rule.when, out):
            continue
        matched.append(rule.id)
        act = rule.then
        if act.set_severity is not None:
            out["severity"] = act.set_severity
        if act.route_to is not None:
            out["route_to"] = act.route_to
        if act.tag is not None:
            tags = list(out.get("tags") or [])
            if act.tag not in tags:
                tags.append(act.tag)
            out["tags"] = tags
        if act.suppress:
            out["__suppressed__"] = True
            return BusinessContextResult(out, matched, True, severity_before, out.get("severity"))
    return BusinessContextResult(out, matched, False, severity_before, out.get("severity"))


#: How long a tenant's rules are cached before re-reading Postgres. Business
#: context changes rarely and this sits on the hot path for every fused alert.
_TENANT_CACHE_TTL_SECONDS = 30.0


class BusinessContextApplier:
    """Applies business-context rules from Postgres, and from a YAML file.

    Rules authored in the console are stored per tenant in
    `aisoc_business_context_rule_sets`. This class only ever read a YAML file
    whose path comes from `AISOC_BUSINESS_CONTEXT_RULES_FILE` — which nothing
    sets — so a tenant could author a rule ("this host is a domain controller,
    escalate anything touching it"), see it saved, preview it against their
    last 50 alerts, and have it apply to no triage decision ever. The console
    and the worker were looking at two different places.

    The file path is kept as an operator-level override: an air-gapped install
    that ships rules on disk should keep working, and its rules apply to every
    tenant. Tenant rules are evaluated first, because a tenant's own statement
    about their estate is more specific than a deployment-wide default.
    """

    def __init__(self, rules_file: str | None = None) -> None:
        self._path = rules_file or os.environ.get(_RULES_FILE_ENV, "")
        self._rules: list[BusinessContextRule] = []
        self._mtime: float | None = None
        self._tenant_rules: dict[str, tuple[float, list[BusinessContextRule]]] = {}
        self._tenant_versions: dict[str, dict[str, Any]] = {}
        self._tenant_load_status: dict[str, str] = {}
        self._file_revision: str | None = None
        self._file_status = "unconfigured"
        #: Set by `seed_tenant_rules` for the replay path. When present, these
        #: replace the Postgres read entirely -- see that method.
        self._seeded_rules: list[BusinessContextRule] | None = None
        self._load()

    # ── tenant rules (Postgres) ───────────────────────────────────────────

    async def _load_tenant_rules(self, tenant_id: str) -> list[BusinessContextRule]:
        """Read and cache the tenant's authored rules. Never raises."""
        if self._seeded_rules is not None:
            self._tenant_load_status[tenant_id] = "seeded"
            return self._seeded_rules
        cached = self._tenant_rules.get(tenant_id)
        now = time.monotonic()
        if cached is not None and now - cached[0] < _TENANT_CACHE_TTL_SECONDS:
            self._tenant_load_status[tenant_id] = "cache"
            return cached[1]

        dsn = os.environ.get("DATABASE_DSN") or os.environ.get("DATABASE_URL") or ""
        dsn = dsn.strip().replace("postgresql+asyncpg://", "postgresql://")
        if not dsn:
            self._tenant_load_status[tenant_id] = "unconfigured"
            return []

        try:
            import asyncpg  # noqa: PLC0415 — optional at import time

            conn = await asyncpg.connect(dsn, timeout=5.0)
            try:
                row = await conn.fetchrow(
                    """
                    SELECT yaml_text, enabled, updated_at
                    FROM aisoc_business_context_rule_sets
                    WHERE tenant_id = $1
                    """,
                    uuid.UUID(tenant_id),
                )
            finally:
                await conn.close()
        except Exception as exc:  # noqa: BLE001 — fail-soft: no tenant rules applied
            logger.warning(
                "business_context.tenant_load_failed",
                tenant_id=tenant_id,
                error=type(exc).__name__,
            )
            # Serve the last known rules rather than silently dropping a
            # tenant's suppressions during a brief outage.
            self._tenant_load_status[tenant_id] = "stale_cache" if cached else "unavailable"
            return cached[1] if cached else []

        rules: list[BusinessContextRule] = []
        if row is not None and row["enabled"] and row["yaml_text"]:
            try:
                rules = load_rules_from_yaml(row["yaml_text"])
            except Exception as exc:  # noqa: BLE001 — a bad rule set applies none
                logger.warning(
                    "business_context.tenant_parse_failed",
                    tenant_id=tenant_id,
                    error=str(exc),
                )
                rules = []

        self._tenant_rules[tenant_id] = (now, rules)
        yaml_text = row["yaml_text"] or "" if row is not None else ""
        enabled = bool(row["enabled"]) if row is not None else True
        updated_at = row.get("updated_at") if row is not None else None
        self._tenant_versions[tenant_id] = {
            "policy_revision": policy_revision(yaml_text, enabled),
            "enabled": enabled,
            "updated_at": updated_at.isoformat() if updated_at else None,
        }
        self._tenant_load_status[tenant_id] = "current" if row is not None else "empty"
        return rules

    async def apply_for_tenant(self, tenant_id: str | None, alert: dict[str, Any]) -> BusinessContextResult:
        """Apply this tenant's authored rules, then any deployment-wide ones."""
        self._load()  # cheap mtime check on the file-based rules
        tenant_rules = await self._load_tenant_rules(str(tenant_id)) if tenant_id else []
        rules = [*tenant_rules, *self._rules]
        provenance = {
            "tenant_id": str(tenant_id) if tenant_id else None,
            **self._tenant_versions.get(str(tenant_id), {}),
            "load_status": self._tenant_load_status.get(str(tenant_id), "unscoped" if not tenant_id else "unobserved"),
            "file_revision": self._file_revision,
            "file_status": self._file_status,
            "cache_ttl_seconds": _TENANT_CACHE_TTL_SECONDS,
        }
        if provenance["load_status"] in {"unconfigured", "unavailable", "seeded", "unscoped", "unobserved"}:
            provenance["policy_revision"] = None
        if not rules:
            return BusinessContextResult(dict(alert), [], False, alert.get("severity"), alert.get("severity"), provenance)
        try:
            result = apply_rules(alert, rules)
            result.provenance = provenance
            return result
        except Exception as exc:  # noqa: BLE001 — never break triage
            logger.warning("business_context.apply_failed", error=str(exc))
            return BusinessContextResult(dict(alert), [], False, alert.get("severity"), alert.get("severity"), {**provenance, "evaluation_failed": True})

    def clear_tenant_cache(self) -> None:
        """Drop cached tenant rules. Used by tests."""
        self._tenant_rules.clear()
        self._tenant_versions.clear()
        self._tenant_load_status.clear()

    def seed_tenant_rules(self, rules: list[BusinessContextRule]) -> None:
        """Apply these rules to every tenant, instead of reading Postgres.

        For the replay path (fix pass 3.1), which holds a rule set frozen at
        the split point and must not re-read the live one: a read would
        reintroduce an edit made after the window being graded, which is the
        leakage the frozen context exists to prevent.

        Seeded under a sentinel rather than per tenant id because a replay
        runs one tenant at a time and the applier is constructed per run, so
        there is no second tenant whose rules this could reach.
        """
        self._seeded_rules = list(rules)

    def _load(self) -> None:
        if not self._path:
            self._rules = []
            self._file_revision, self._file_status = None, "unconfigured"
            return
        try:
            p = Path(self._path)
            if not p.exists():
                self._rules = []
                self._file_revision, self._file_status = None, "missing"
                return
            mtime = p.stat().st_mtime
            if mtime == self._mtime:
                return
            yaml_text = p.read_text(encoding="utf-8")
            self._rules = load_rules_from_yaml(yaml_text)
            self._file_revision, self._file_status = policy_revision(yaml_text, True), "current"
            self._mtime = mtime
            logger.info("business_context.rules_loaded", count=len(self._rules), path=self._path)
        except Exception as exc:  # noqa: BLE001 — fail-soft: no rules applied
            logger.warning("business_context.load_failed", error=str(exc), path=self._path)
            self._rules = []
            self._file_revision, self._file_status = None, "error"

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def apply(self, alert: dict[str, Any]) -> BusinessContextResult:
        self._load()  # cheap mtime check; reload only when the file changed
        if not self._rules:
            return BusinessContextResult(dict(alert), [], False, alert.get("severity"), alert.get("severity"))
        try:
            return apply_rules(alert, self._rules)
        except Exception as exc:  # noqa: BLE001 — never break triage
            logger.warning("business_context.apply_failed", error=str(exc))
            return BusinessContextResult(dict(alert), [], False, alert.get("severity"), alert.get("severity"))
