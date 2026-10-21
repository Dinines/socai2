"""Incident context traversal: one query, five dimensions, tenant-scoped.

An investigation needs to answer five questions about an alert, and until now
each was a separate round trip or was not answerable at all:

    identity  Which person is behind the account, what team, who is their
              manager, are they still employed?
    asset     What host, who owns it, what does it run, what is exploitable
              on it right now?
    cloud     Which account, which workload, what secrets does it reach?
    business  Which business application, how critical, what data class,
              who is accountable?
    threat    Which indicators, which malware family, which campaign, which
              actor, which techniques?

``get_blast_radius`` answers "what is reachable" but not "what does any of it
mean" — it returns a node set, unlabelled by dimension, so a caller has to
re-derive the structure. This returns the five dimensions separately, which
is what a narrative and a prompt both need.

Three properties are load-bearing:

**Tenant scoping on every node of every path.** Not just the start node: an
expansion through a shared entity (a public IP both tenants have seen) is how
a traversal leaves its tenant. Global reference labels — MITRE technique and
tactic vocabulary, public malware and actor intel — are exempt, because
requiring a tenant_id on them makes them unreachable for everyone.

**Bounded fan-out.** Every leg has its own LIMIT. An unbounded traversal from
a busy host is not slow, it is unbounded, and this sits on the hot path of
every escalated alert.

**Partial results are reported as partial.** One dimension failing returns
the other four with the failure named, rather than an empty bundle that reads
as "no context exists" — which is the same output an agent gets for a genuinely
isolated alert, and the two must not be confused.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, time
from typing import Any

from app.db import neo4j as neo4j_db
from app.db.neo4j import get_session

logger = logging.getLogger("aisoc.incident_context")

#: Reference entities shared across tenants. Must match
#: ``graph.GlobalNodeLabels`` in services/ingest/internal/graph/schema.go.
GLOBAL_LABELS = (
    "Technique",
    "Tactic",
    "Mitigation",
    "Malware",
    "Campaign",
    "ThreatActor",
    # A CVE is the same fact in every tenant and the node carries no
    # tenant data. What is tenant-specific is the AFFECTED_BY edge from a
    # scoped Resource, so the node is global and only ever reached as a
    # terminal hop — never traversed *through*, which would make it a
    # bridge between two tenants' estates.
    "Vulnerability",
)

_SCOPED = "({v}.tenant_id = $tenant_id OR any(l IN labels({v}) WHERE l IN $global_labels))"

# Per-dimension caps. A traversal from a jump host or a shared service
# account can otherwise fan out across the estate.
LIMIT_IDENTITIES = 25
LIMIT_ASSETS = 25
LIMIT_VULNS = 20
LIMIT_CLOUD = 15
LIMIT_BUSINESS = 15
LIMIT_THREAT = 25

# Neo4j default timeout is unbounded. On the hot path of every escalated
# alert, an unbounded read is an outage waiting for its busiest tenant.
QUERY_TIMEOUT_SECONDS = 8.0


def _scoped(var: str) -> str:
    return _SCOPED.format(v=var)


@dataclass
class IncidentContext:
    """The five dimensions, plus what failed while gathering them."""

    alert_id: str
    tenant_id: str
    identities: list[dict[str, Any]] = field(default_factory=list)
    assets: list[dict[str, Any]] = field(default_factory=list)
    cloud: list[dict[str, Any]] = field(default_factory=list)
    business: list[dict[str, Any]] = field(default_factory=list)
    threat: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def dimensions_resolved(self) -> int:
        return sum(1 for d in (self.identities, self.assets, self.cloud, self.business, self.threat) if d)

    @property
    def is_partial(self) -> bool:
        return bool(self.errors)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["dimensions_resolved"] = self.dimensions_resolved
        payload["partial"] = self.is_partial
        return payload

    def narrative_lines(self) -> list[str]:
        """Render as prompt-ready lines.

        Deliberately omits anything an agent should not reason over: secret
        *values* are never in the graph, and node internals are not useful to
        a model. What is included is what changes a verdict.
        """
        lines: list[str] = []

        for person in self.identities[:5]:
            bits = [f"account {person.get('account') or 'unknown'}"]
            if person.get("employee"):
                bits.append(f"held by {person['employee']}")
            if person.get("title"):
                bits.append(person["title"])
            if person.get("department"):
                bits.append(f"in {person['department']}")
            if person.get("manager"):
                bits.append(f"reports to {person['manager']}")
            # A departed employee with a live account is the single
            # highest-signal fact this traversal can surface.
            if person.get("is_active") is False:
                bits.append("**employee is no longer active**")
            lines.append("- Identity: " + ", ".join(bits))

        for asset in self.assets[:5]:
            bits = [asset.get("name") or asset.get("id") or "unknown host"]
            if asset.get("owner"):
                bits.append(f"owned by {asset['owner']}")
            vulns = asset.get("vulnerabilities") or []
            if vulns:
                kev = [v for v in vulns if v.get("known_exploited")]
                bits.append(f"{len(vulns)} known vulnerabilities" + (f", {len(kev)} known-exploited" if kev else ""))
            lines.append("- Asset: " + ", ".join(bits))

        for account in self.cloud[:5]:
            bits = [f"{account.get('provider') or 'cloud'} account {account.get('account_id')}"]
            if account.get("environment"):
                bits.append(account["environment"])
            if account.get("secret_count"):
                bits.append(f"{account['secret_count']} reachable secret references")
            lines.append("- Cloud: " + ", ".join(bits))

        for app in self.business[:5]:
            bits = [app.get("name") or "unknown application"]
            if app.get("criticality"):
                bits.append(f"criticality {app['criticality']}")
            if app.get("data_classification"):
                bits.append(f"data {app['data_classification']}")
            if app.get("owner"):
                bits.append(f"business owner {app['owner']}")
            if app.get("internet_facing"):
                bits.append("internet-facing")
            lines.append("- Business: " + ", ".join(bits))

        for threat in self.threat[:5]:
            bits = [f"{threat.get('ioc_type') or 'indicator'} {threat.get('ioc')}"]
            if threat.get("malware"):
                bits.append(f"associated with {threat['malware']}")
            if threat.get("actor"):
                confidence = threat.get("attribution_confidence")
                # Attribution is contested and frequently revised, so it is
                # never rendered as fact.
                suffix = f" (attribution confidence {confidence})" if confidence else " (attribution unconfirmed)"
                bits.append(f"attributed to {threat['actor']}{suffix}")
            if threat.get("techniques"):
                bits.append("techniques " + ", ".join(threat["techniques"][:4]))
            lines.append("- Threat: " + ", ".join(bits))

        if self.errors:
            lines.append("- NOTE: context is partial; these dimensions could not be read: " + ", ".join(self.errors))
        return lines


# ── Cypher, one query per dimension ─────────────────────────────────────────
# Split rather than combined: a single query would make one slow leg slow
# everything, and one failing leg fail everything.

_IDENTITY_CYPHER = f"""
MATCH (a:Alert {{id: $alert_id}})
WHERE {_scoped("a")}
MATCH (a)-[:OCCURRED_ON|INVOLVES*1..2]-(i:Identity)
WHERE {_scoped("i")}
OPTIONAL MATCH (e:Employee)-[:AUTHENTICATES_AS]->(i)
WHERE {_scoped("e")}
OPTIONAL MATCH (e)-[:BELONGS_TO]->(d:Department)
WHERE {_scoped("d")}
OPTIONAL MATCH (mgr:Employee)-[:MANAGES]->(e)
WHERE {_scoped("mgr")}
RETURN DISTINCT
    i.external_id      AS account,
    i.provider         AS provider,
    e.display_name     AS employee,
    e.title            AS title,
    e.is_active        AS is_active,
    d.name             AS department,
    mgr.display_name   AS manager,
    mgr.email          AS manager_email
LIMIT $limit
"""

_ASSET_CYPHER = f"""
MATCH (a:Alert {{id: $alert_id}})
WHERE {_scoped("a")}
MATCH (a)-[:OCCURRED_ON|INVOLVES*1..2]-(r:Resource)
WHERE {_scoped("r")}
OPTIONAL MATCH (owner:Identity)-[:OWNS]->(r)
WHERE {_scoped("owner")}
OPTIONAL MATCH (r)-[:AFFECTED_BY]->(v:Vulnerability)
WITH r, owner, v
ORDER BY coalesce(v.known_exploited, false) DESC, coalesce(v.cvss_score, 0) DESC
WITH r, owner, collect(DISTINCT {{
    cve_id: v.cve_id,
    cvss_score: v.cvss_score,
    known_exploited: v.known_exploited
}})[..$vuln_limit] AS vulns
RETURN DISTINCT
    r.id                 AS id,
    coalesce(r.name, r.hostname) AS name,
    r.resource_type      AS resource_type,
    owner.display_name   AS owner,
    [x IN vulns WHERE x.cve_id IS NOT NULL] AS vulnerabilities
LIMIT $limit
"""

_CLOUD_CYPHER = f"""
MATCH (a:Alert {{id: $alert_id}})
WHERE {_scoped("a")}
MATCH (a)-[:OCCURRED_ON|INVOLVES*1..2]-(r:Resource)
WHERE {_scoped("r")}
MATCH (r)-[:IN_ACCOUNT]->(ca:CloudAccount)
WHERE {_scoped("ca")}
OPTIONAL MATCH (r)-[:STORES]->(s:Secret)
WHERE {_scoped("s")}
RETURN DISTINCT
    ca.account_id  AS account_id,
    ca.provider    AS provider,
    ca.name        AS name,
    ca.environment AS environment,
    count(DISTINCT s) AS secret_count
LIMIT $limit
"""

_BUSINESS_CYPHER = f"""
MATCH (a:Alert {{id: $alert_id}})
WHERE {_scoped("a")}
MATCH (a)-[:OCCURRED_ON|INVOLVES*1..2]-(r:Resource)
WHERE {_scoped("r")}
MATCH (r)-[:RUNS]->(app:Application)
WHERE {_scoped("app")}
OPTIONAL MATCH (app)-[:OWNED_BY]->(bo:Employee)
WHERE {_scoped("bo")}
RETURN DISTINCT
    app.name                AS name,
    app.criticality         AS criticality,
    app.data_classification AS data_classification,
    app.revenue_impact      AS revenue_impact,
    app.environment         AS environment,
    app.internet_facing     AS internet_facing,
    app.compliance_scope    AS compliance_scope,
    bo.display_name         AS owner,
    bo.email                AS owner_email
LIMIT $limit
"""

_THREAT_CYPHER = f"""
MATCH (a:Alert {{id: $alert_id}})
WHERE {_scoped("a")}
MATCH (a)-[:OBSERVED_IOC]->(ioc:IOC)
WHERE {_scoped("ioc")}
OPTIONAL MATCH (ioc)-[:INDICATES]->(m:Malware)
OPTIONAL MATCH (m)-[:PART_OF]->(c:Campaign)
OPTIONAL MATCH (c)-[attr:ATTRIBUTED_TO]->(actor:ThreatActor)
OPTIONAL MATCH (m)-[:USES_TECHNIQUE]->(t:Technique)
RETURN DISTINCT
    ioc.value  AS ioc,
    ioc.type   AS ioc_type,
    m.name     AS malware,
    c.name     AS campaign,
    actor.name AS actor,
    attr.confidence AS attribution_confidence,
    collect(DISTINCT t.id)[..6] AS techniques
LIMIT $limit
"""

_DIMENSIONS: tuple[tuple[str, str, dict[str, int]], ...] = (
    ("identities", _IDENTITY_CYPHER, {"limit": LIMIT_IDENTITIES}),
    ("assets", _ASSET_CYPHER, {"limit": LIMIT_ASSETS, "vuln_limit": LIMIT_VULNS}),
    ("cloud", _CLOUD_CYPHER, {"limit": LIMIT_CLOUD}),
    ("business", _BUSINESS_CYPHER, {"limit": LIMIT_BUSINESS}),
    ("threat", _THREAT_CYPHER, {"limit": LIMIT_THREAT}),
)


async def _run_dimension(session: Any, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    result = await session.run(cypher, **params)
    rows = await result.data()
    # Neo4j returns every RETURN key even when the OPTIONAL MATCH produced
    # nothing, so a row can be entirely nulls. Dropping empty keys keeps the
    # payload readable and stops a prompt rendering "manager: None".
    return [{k: v for k, v in row.items() if v not in (None, [], "")} for row in rows]


#: Identity context keyed on the account names an alert carries, rather than
#: traversed from an ``Alert`` node. Gap-closure Phase 6.3.
#:
#: The dimension query above starts at ``(a:Alert {id: $alert_id})``, which is
#: the right shape for an escalated alert whose node the ingest writer has
#: already created. Triage runs earlier than that, and a replayed historical
#: finding has no ``Alert`` node at all, so keying on the account names is the
#: only version of this question triage can ask.
#:
# This query intentionally does not use _scoped: no global-label exemption
# applies to identity/HR nodes, including nodes with mixed labels. Counts are
# over distinct node paths for the bounded requested accounts, before limit.
# Only native zoned datetimes can be compared. Text is never parsed in Cypher:
# datetime(arbitrary_text) would make one malformed property fail the read.
_IDENTITY_BY_ACCOUNT_CYPHER = """
MATCH (i:Identity)
WHERE i.tenant_id = $tenant_id AND toLower(i.external_id) IN $accounts
OPTIONAL MATCH (e:Employee)-[:AUTHENTICATES_AS]->(i)
WHERE e.tenant_id = $tenant_id
OPTIONAL MATCH (e)-[:BELONGS_TO]->(d:Department)
WHERE d.tenant_id = $tenant_id
OPTIONAL MATCH (mgr:Employee)-[:MANAGES]->(e)
WHERE mgr.tenant_id = $tenant_id
WITH DISTINCT i, e, d, mgr
WITH i, e, d, mgr,
     CASE WHEN e.updated_at IS NOT NULL AND e.updated_at IS :: ZONED DATETIME
          THEN e.updated_at ELSE null END AS stamp,
     CASE WHEN e.updated_at IS NULL THEN 'missing'
          WHEN e.updated_at IS :: ZONED DATETIME THEN 'native'
          ELSE 'unsupported' END AS stamp_status
WITH collect({
    stamp: stamp,
    row: {
        identity_id: CASE WHEN i.id IS NULL OR trim(toString(i.id)) = '' THEN elementId(i) ELSE toString(i.id) END,
        identity_id_kind: CASE WHEN i.id IS NULL OR trim(toString(i.id)) = '' THEN 'element_id' ELSE 'business_id' END,
        employee_id: CASE WHEN e IS NULL THEN null WHEN e.id IS NULL OR trim(toString(e.id)) = '' THEN elementId(e) ELSE toString(e.id) END,
        employee_id_kind: CASE WHEN e IS NULL THEN null WHEN e.id IS NULL OR trim(toString(e.id)) = '' THEN 'element_id' ELSE 'business_id' END,
        department_id: CASE WHEN d IS NULL THEN null WHEN d.id IS NULL OR trim(toString(d.id)) = '' THEN elementId(d) ELSE toString(d.id) END,
        department_id_kind: CASE WHEN d IS NULL THEN null WHEN d.id IS NULL OR trim(toString(d.id)) = '' THEN 'element_id' ELSE 'business_id' END,
        manager_id: CASE WHEN mgr IS NULL THEN null WHEN mgr.id IS NULL OR trim(toString(mgr.id)) = '' THEN elementId(mgr) ELSE toString(mgr.id) END,
        manager_id_kind: CASE WHEN mgr IS NULL THEN null WHEN mgr.id IS NULL OR trim(toString(mgr.id)) = '' THEN 'element_id' ELSE 'business_id' END,
        account: i.external_id, provider: i.provider,
        employee: e.display_name, title: e.title, is_active: e.is_active,
        employment_type: e.employment_type, start_date: e.start_date, end_date: e.end_date,
        imported_at: stamp, imported_at_status: stamp_status,
        imported_at_raw: e.updated_at,
        department: d.name, manager: mgr.display_name, manager_email: mgr.email,
        employee_linked: e IS NOT NULL,
        relationship_source: {
            employee_identity: CASE WHEN e IS NULL THEN null ELSE 'AUTHENTICATES_AS' END,
            employee_department: CASE WHEN d IS NULL THEN null ELSE 'BELONGS_TO' END,
            manager_employee: CASE WHEN mgr IS NULL THEN null ELSE 'MANAGES' END
        }
    }
}) AS candidates
WITH candidates,
     [c IN candidates WHERE $as_of IS NULL OR
         (c.row.imported_at_status = 'native' AND c.stamp <= $as_of)] AS eligible
CALL {
    WITH eligible
    UNWIND eligible AS c
    WITH c
    ORDER BY toLower(c.row.account), coalesce(c.row.provider, ''),
             c.row.identity_id, coalesce(c.row.employee_id, ''),
             coalesce(c.row.department_id, ''), coalesce(c.row.manager_id, '')
    LIMIT $limit
    RETURN collect(c.row) AS identities
}
RETURN identities, size(candidates) AS candidate_count, size(eligible) AS eligible_count,
       size(eligible) - size(identities) AS truncated_count,
       size([c IN candidates WHERE $as_of IS NOT NULL AND
           c.row.imported_at_status = 'native' AND c.stamp > $as_of]) AS excluded_after_cutoff,
       size([c IN candidates WHERE $as_of IS NOT NULL AND
           c.row.imported_at_status <> 'native']) AS excluded_unverifiable_import,
       size([c IN candidates WHERE c.row.imported_at_status = 'missing']) AS import_timestamp_missing
"""


IDENTITY_SOURCE_FIELDS = (
    "identity_id", "identity_id_kind", "employee_id", "employee_id_kind",
    "department_id", "department_id_kind", "manager_id", "manager_id_kind",
    "account", "provider", "employee", "title", "is_active", "employment_type",
    "start_date", "end_date", "imported_at", "imported_at_status",
    "imported_at_raw_sha256", "department", "manager", "manager_email",
    "employee_linked", "relationship_source",
)


@dataclass
class IdentityAccountRead:
    """Current graph projection; an import cutoff never proves HR history."""

    status: str
    reason: str | None = None
    identities: list[dict[str, Any]] = field(default_factory=list)
    as_of: datetime | None = None
    candidate_count: int = 0
    eligible_count: int = 0
    truncated_count: int = 0
    excluded_after_cutoff: int = 0
    excluded_unverifiable_import: int = 0
    import_timestamp_missing: int = 0
    without_timestamp: int = 0


def _identity_json(value: Any) -> Any:
    """Normalize driver temporal values before hashing or HTTP serialization."""
    to_native = getattr(value, "to_native", None)
    if callable(to_native):
        value = to_native()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.isoformat()
        return value.astimezone(UTC).isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, (tuple, list)):
        return [_identity_json(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _identity_json(item) for key, item in value.items()}
    raise ValueError("Unsupported identity graph property type")


def _identity_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _identity_projection(row: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    projected = {key: _identity_json(row.get(key)) for key in IDENTITY_SOURCE_FIELDS if key != "imported_at_raw_sha256"}
    projected["imported_at_raw_sha256"] = _identity_hash(_identity_json(row.get("imported_at_raw")))
    if not isinstance(projected["identity_id"], str) or not projected["identity_id"]:
        raise ValueError("Missing identity node identifier")
    if not isinstance(projected["account"], str) or not projected["account"].strip():
        raise ValueError("Missing identity account")
    for key in ("provider", "employee", "title", "employment_type", "start_date", "end_date",
                "department", "manager", "manager_email"):
        if projected[key] is not None and not isinstance(projected[key], str):
            raise ValueError("Non-text identity projection field")
    for node in ("identity", "employee", "department", "manager"):
        node_id, kind = projected[node + "_id"], projected[node + "_id_kind"]
        if node_id is None:
            if kind is not None:
                raise ValueError("Identity node identifier kind without a node")
        elif not isinstance(node_id, str) or not node_id or kind not in {"business_id", "element_id"}:
            raise ValueError("Invalid identity node identifier projection")
    linked = projected["employee_linked"]
    if type(linked) is not bool or linked != (projected["employee_id"] is not None):
        raise ValueError("Invalid employee association")
    if not linked and (projected["department_id"] is not None or projected["manager_id"] is not None):
        raise ValueError("Identity path has no employee association")
    relationships = {
        "employee_identity": "AUTHENTICATES_AS" if linked else None,
        "employee_department": "BELONGS_TO" if projected["department_id"] is not None else None,
        "manager_employee": "MANAGES" if projected["manager_id"] is not None else None,
    }
    if projected["relationship_source"] != relationships:
        raise ValueError("Identity relationship provenance does not match its node path")
    # A non-boolean legacy property is unknown; it must never become True by
    # Python truthiness (notably the string "false").
    if type(projected["is_active"]) is not bool:
        projected["is_active"] = None
    if projected["imported_at_status"] not in {"native", "missing", "unsupported"}:
        raise ValueError("Invalid import timestamp classification")
    if projected["imported_at_status"] == "native":
        stamp = row.get("imported_at")
        to_native = getattr(stamp, "to_native", None)
        if callable(to_native):
            stamp = to_native()
        if not isinstance(stamp, datetime) or stamp.tzinfo is None:
            raise ValueError("Native import stamp is not a zoned datetime")
        projected["imported_at"] = stamp.astimezone(UTC).isoformat()
    else:
        projected["imported_at"] = None
    projected["row_source_sha256"] = _identity_hash({"tenant_id": str(tenant_id), **projected})
    return projected


def _identity_failure_reason(exc: Exception) -> str:
    name = type(exc).__name__
    if name == "IdentityGraphNotConfigured":
        return "graph_not_configured"
    if isinstance(exc, TimeoutError):
        return "graph_timeout"
    if name in {"AuthError", "TokenExpired", "Forbidden", "SecurityError"}:
        return "graph_auth_failed"
    if isinstance(exc, (ConnectionError, OSError)) or name in {"ServiceUnavailable", "SessionExpired"}:
        return "graph_unavailable"
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return "invalid_source_response"
    return "graph_query_failed"


async def read_identity_context_for_accounts(
    tenant_id: str,
    accounts: list[str],
    *,
    limit: int = LIMIT_IDENTITIES,
    as_of: datetime | None = None,
    session: Any | None = None,
) -> IdentityAccountRead:
    """Read bounded accounts with explicit availability and current provenance.

    The dedicated session never initializes the general graph driver/schema.
    Employee import time can exclude late or uncomparable current rows; all
    surviving rows remain unproven as business facts at the historical split.
    """
    normalised = sorted({a.strip().lower() for a in accounts if isinstance(a, str) and a.strip()})
    if len(normalised) > 25 or not 1 <= limit <= LIMIT_IDENTITIES:
        raise ValueError("Identity account/row limit exceeded")
    if as_of is not None:
        if as_of.tzinfo is None:
            raise ValueError("Identity cutoff must include a timezone")
        as_of = as_of.astimezone(UTC)
    if not normalised:
        return IdentityAccountRead(status="no_match", as_of=as_of)

    async def _run(sess: Any) -> IdentityAccountRead:
        result = await sess.run(_IDENTITY_BY_ACCOUNT_CYPHER, tenant_id=str(tenant_id),
                                accounts=normalised, limit=limit, as_of=as_of)
        envelopes = await result.data()
        if len(envelopes) != 1:
            raise ValueError("Identity query must return one count envelope")
        envelope = envelopes[0]
        count_fields = ("candidate_count", "eligible_count", "truncated_count", "excluded_after_cutoff",
                        "excluded_unverifiable_import", "import_timestamp_missing")
        counts = {key: envelope[key] for key in count_fields}
        if any(type(value) is not int or value < 0 for value in counts.values()):
            raise ValueError("Invalid identity query counts")
        rows = [_identity_projection(row, str(tenant_id)) for row in envelope["identities"]]
        if (counts["candidate_count"] != counts["eligible_count"] + counts["excluded_after_cutoff"] + counts["excluded_unverifiable_import"]
                or counts["eligible_count"] != len(rows) + counts["truncated_count"]
                or counts["import_timestamp_missing"] > counts["candidate_count"] or len(rows) > limit):
            raise ValueError("Identity query count relationships do not hold")
        if sum(row["imported_at_status"] == "missing" for row in rows) > counts["import_timestamp_missing"]:
            raise ValueError("Identity missing-import count does not cover returned rows")
        if any(row["account"].strip().lower() not in normalised for row in rows):
            raise ValueError("Identity account escaped the requested set")
        if as_of is None and (counts["excluded_after_cutoff"] or counts["excluded_unverifiable_import"]):
            raise ValueError("Live identity read unexpectedly applied a cutoff")
        if as_of is not None and any(row["imported_at_status"] != "native"
                                    or datetime.fromisoformat(row["imported_at"]) > as_of for row in rows):
            raise ValueError("Identity import cutoff was not honored")
        if as_of is not None and counts["excluded_unverifiable_import"] < counts["import_timestamp_missing"]:
            raise ValueError("Frozen identity read did not exclude every missing import stamp")
        return IdentityAccountRead(status="success" if rows else "no_match", identities=rows,
                                   as_of=as_of, without_timestamp=len(rows), **counts)

    try:
        if session is not None:
            return await asyncio.wait_for(_run(session), timeout=QUERY_TIMEOUT_SECONDS)
        async with neo4j_db.get_identity_read_session() as sess:
            return await asyncio.wait_for(_run(sess), timeout=QUERY_TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001 - return a typed failure, never normal empty data
        reason = _identity_failure_reason(exc)
        logger.warning("identity_context.unavailable reason=%s exception_type=%s", reason, type(exc).__name__)
        return IdentityAccountRead(status="unavailable", reason=reason, as_of=as_of)


async def get_identity_context_for_accounts(
    tenant_id: str, accounts: list[str], *, limit: int = LIMIT_IDENTITIES,
    session: Any | None = None,
) -> list[dict[str, Any]]:
    """Legacy list projection; new callers must inspect the typed read status."""
    found = await read_identity_context_for_accounts(tenant_id, accounts, limit=limit, session=session)
    return found.identities


async def get_incident_context(
    alert_id: str,
    tenant_id: str,
    *,
    session: Any | None = None,
) -> IncidentContext:
    """Traverse an alert into all five context dimensions.

    Dimensions run concurrently and independently: one failure names itself in
    ``errors`` and the rest still return. An empty bundle with no errors means
    the alert genuinely has no context, which is a different finding from a
    graph that was unreachable.
    """
    context = IncidentContext(alert_id=alert_id, tenant_id=tenant_id)
    # alert_id arrives from a URL path, so it is attacker-controlled and can
    # forge log lines with CR/LF. Sanitised inline rather than via a helper:
    # the taint tracker does not follow a helper across a function boundary,
    # and this shape is the repo's documented convention.
    safe_alert_id = str(alert_id).replace("\r", "").replace("\n", " ")[:120]

    async def _gather(sess: Any) -> None:
        base = {
            "alert_id": alert_id,
            "tenant_id": tenant_id,
            "global_labels": list(GLOBAL_LABELS),
        }

        async def one(name: str, cypher: str, extra: dict[str, int]) -> tuple[str, Any]:
            try:
                rows = await asyncio.wait_for(
                    _run_dimension(sess, cypher, {**base, **extra}),
                    timeout=QUERY_TIMEOUT_SECONDS,
                )
                return name, rows
            except TimeoutError:
                logger.warning(
                    "incident_context.%s timed out after %.1fs alert=%s",
                    name,
                    QUERY_TIMEOUT_SECONDS,
                    safe_alert_id,
                )
                return name, TimeoutError(f"{name}: timeout")
            except Exception as exc:
                logger.warning(
                    "incident_context.%s failed alert=%s err=%s",
                    name,
                    safe_alert_id,
                    type(exc).__name__,
                )
                return name, exc

        results = await asyncio.gather(*(one(name, cypher, extra) for name, cypher, extra in _DIMENSIONS))
        for name, value in results:
            if isinstance(value, Exception):
                context.errors.append(f"{name} ({type(value).__name__})")
            else:
                setattr(context, name, value)

    try:
        if session is not None:
            await _gather(session)
        else:
            async with get_session() as sess:
                await _gather(sess)
    except Exception as exc:
        # The graph being unreachable must not be indistinguishable from an
        # alert with no context.
        context.errors.append(f"graph unavailable ({type(exc).__name__})")
        logger.warning("incident_context.unavailable alert=%s err=%s", safe_alert_id, type(exc).__name__)

    logger.info(
        "incident_context alert=%s tenant=%s dimensions=%d partial=%s",
        safe_alert_id,
        tenant_id,
        context.dimensions_resolved,
        context.is_partial,
    )
    return context
