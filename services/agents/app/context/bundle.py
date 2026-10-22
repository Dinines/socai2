"""ContextBundle model + builder — T2.1.

A :class:`ContextBundle` is the *pre-fetched* context object that the four
public agents (Detect / Triage / Hunt / Respond) and their internal
capability shims (phishing, identity, cloud, insider-threat) consume in
place of issuing their own primary-discovery tool calls.

The builder fans out to four read-only context sources concurrently:

* graph neighbourhood (``services/api`` — depth-N walk per principal entity),
* institutional memory (``aisoc_institutional_memory`` — similar-case
  verdicts keyed by template / category / IOC tag),
* UEBA baselines (``services/ueba`` — per-entity peer baseline + deviation),
* threat intel (``services/enrichment`` — per-IOC reputation + risk).

Every field is optional and the bundle is allowed to be partial — a
context source that times out, errors, or is unavailable populates the
``errors`` list and leaves its slot empty so the consumer can fall back
to its own primary-discovery code path. Tests gate the *build latency*
(p95 < 5s across the 200-incident benchmark), not the *contents*, because
the eval harness runs offline against substrate stubs.

The model is the *only* shape an agent should hand to the LLM-input
contract (T2.3) — its ``summary_for_llm`` method returns a dict whose
keys are explicitly enumerated as allowed by ``LLMInputContract``.
"""

from __future__ import annotations

import asyncio
import math
import os
import re
import time
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------

# Map of raw_alert key → entity type. Order matters only insofar as it controls
# which alias is preferred when several keys point at the same logical entity.
_HOST_KEYS = (
    "host",
    "hostname",
    "Computer",
    "computer",
    "device",
    "asset",
    "endpoint",
    "affected_hosts",
)
_USER_KEYS = (
    "user",
    "username",
    "user_email",
    "UserId",
    "principal",
    "actor",
    "sender",
    "recipient",
    "affected_users",
)
_IP_KEYS = (
    "src_ip",
    "source_ip",
    "ClientIP",
    "client_ip",
    "dst_ip",
    "dest_ip",
    "destination_ip",
    "remote_ip",
    "ip",
    "affected_ips",
)
_DOMAIN_KEYS = ("domain", "sender_domain", "fqdn", "host_domain")
_HASH_KEYS = ("file_hash", "sha256", "md5", "sha1", "hash")
_URL_KEYS = ("url", "primary_url")

_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_DOMAIN_RE = re.compile(r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b", re.IGNORECASE)
_HASH_RE = re.compile(r"\b[a-f0-9]{32}\b|\b[a-f0-9]{40}\b|\b[a-f0-9]{64}\b", re.IGNORECASE)
_CASE_ALERT_LIMIT = 3  # The default Case investigation proxy sends this bounded head.


class EntityRef(BaseModel):
    """Stable reference to an entity in the alert.

    ``key`` is the canonical join key used as the dict key in
    ``entity_neighborhoods`` / ``peer_baselines`` / ``threat_intel``.
    """

    type: str  # host | user | ip | domain | hash | url | email
    value: str

    @property
    def key(self) -> str:
        return f"{self.type}:{self.value}"


def _string_field(raw: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for key in keys:
        val = raw.get(key)
        values = val if isinstance(val, (list, tuple)) else [val]
        for value in values:
            if isinstance(value, str) and value.strip():
                out.append(value.strip())
    return out


def extract_entities(raw_alert: dict[str, Any], *, summary: str = "") -> list[EntityRef]:
    """Extract a deduplicated list of entities from the raw alert + summary.

    Pulled out into a top-level function so the builder's tests can hit it
    directly without spinning up the full builder.
    """
    found: dict[str, EntityRef] = {}

    def _add(etype: str, value: str) -> None:
        value = value.strip()
        if not value:
            return
        ref = EntityRef(type=etype, value=value)
        found.setdefault(ref.key, ref)

    linked = raw_alert.get("alerts")
    materials = [raw_alert] + ([row for row in linked[:_CASE_ALERT_LIMIT] if isinstance(row, dict)]
                             if isinstance(linked, list) else [])
    for material in materials:
        for v in _string_field(material, _HOST_KEYS):
            _add("host", v)
        for v in _string_field(material, _USER_KEYS):
            etype = "email" if "@" in v else "user"
            _add(etype, v)
        for v in _string_field(material, _IP_KEYS):
            _add("ip", v)
        for v in _string_field(material, _DOMAIN_KEYS):
            _add("domain", v.lower())
        for v in _string_field(material, _HASH_KEYS):
            _add("hash", v.lower())
        for v in _string_field(material, _URL_KEYS):
            _add("url", v)

    # Best-effort regex sweep over the alert summary so generic alerts that
    # only carry a free-text description still get an entity vector. The
    # summary regexes run on the joined text so we don't miss IOCs that
    # straddle a boundary.
    text = " ".join([summary or "", *(str(row.get(key, "")) for row in materials for key in ("description", "title"))])
    for ip in _IPV4_RE.findall(text):
        _add("ip", ip)
    for h in _HASH_RE.findall(text):
        _add("hash", h.lower())
    for d in _DOMAIN_RE.findall(text):
        # Filter out things that look like file extensions / version numbers
        # by requiring a TLD of length >= 2 and a body of length >= 4.
        if len(d) >= 6 and "." in d:
            _add("domain", d.lower())

    return list(found.values())


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class EntityNeighborhood(BaseModel):
    """Result of a depth-N graph walk centred on a single entity."""

    entity: EntityRef
    depth: int = 2
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    blast_radius_score: float | None = None
    summary: str = ""

    @property
    def node_count(self) -> int:
        return len(self.nodes)


class HistoricalCase(BaseModel):
    """A previously-closed case judged similar to the current alert.

    Pulled from ``aisoc_institutional_memory`` (PostgreSQL with an in-process
    fallback). ``similarity_score`` is computed by the builder using a
    deterministic Jaccard over template_id / response_class / IOC tags so
    eval runs are reproducible.
    """

    key: str
    verdict: str
    confidence: float = 0.0
    template_id: str | None = None
    response_class: str | None = None
    similarity_score: float = 0.0
    rationale: str | None = None
    closed_at: str | None = None


class UEBABaseline(BaseModel):
    """Per-entity UEBA baseline + peer-group deviation.

    Mirrors the shape returned by ``services/ueba`` ``/api/v1/ueba/baselines``
    so the bundle can pass through what the UEBA service computed without
    re-deriving it.
    """

    entity: EntityRef
    peer_group_id: str | None = None
    activity_window_days: int = 30
    baseline: dict[str, Any] = Field(default_factory=dict)
    deviation_score: float | None = None
    notes: str = ""


class ThreatIntelMatch(BaseModel):
    """Per-IOC enrichment record."""

    ioc: str
    ioc_type: str
    sources: list[str] = Field(default_factory=list)
    risk: str = "unknown"  # low | medium | high | unknown
    first_seen: str | None = None
    last_seen: str | None = None
    summary: str = ""


# ---------------------------------------------------------------------------
# ContextBundle
# ---------------------------------------------------------------------------


# Allowed top-level keys in ``summary_for_llm`` — kept here (not in
# ``app/llm/contract.py``) so the model is the source of truth and the
# contract validator can import this whitelist. Public (no leading
# underscore) because it is imported by tests and by external contract
# validators; the previous private-with-suppression form tripped CodeQL
# ``py/unused-global-variable`` because the inline suppression marker
# was not honoured by the analyzer.
LLM_SAFE_KEYS = (
    "incident_id",
    "alert_summary",
    "entity_count",
    "entity_types",
    "entity_keys",
    "neighborhood_summaries",
    "blast_radius_max",
    "historical_similar_count",
    "historical_verdicts",
    "ueba_max_deviation",
    "ueba_entities_with_baseline",
    "threat_intel_high_risk_iocs",
    "threat_intel_match_count",
    "threat_intel_sources",
    "build_latency_ms",
    "sources_called",
    "errors",
    "attack_context_summary",
)


class IncidentContextDimensions(BaseModel):
    """Identity, asset, cloud, business and threat context for the alert.

    Distinct from ``entity_neighborhoods``, which answers "what is reachable"
    as an undifferentiated node set. This answers "what does it mean": which
    person is behind the account, what is exploitable on the host, which
    business application it serves, who is accountable, and which actor the
    indicators point at. A narrative and a prompt both need the dimensions
    kept apart; a node set makes the caller re-derive them.
    """

    identities: list[dict[str, Any]] = Field(default_factory=list)
    assets: list[dict[str, Any]] = Field(default_factory=list)
    cloud: list[dict[str, Any]] = Field(default_factory=list)
    business: list[dict[str, Any]] = Field(default_factory=list)
    threat: list[dict[str, Any]] = Field(default_factory=list)
    narrative: list[str] = Field(default_factory=list)
    # True when some dimensions could not be read. Without this an agent
    # cannot distinguish "this alert has no context" from "we could not
    # look", and will reason as though the first were true.
    partial: bool = False
    errors: list[str] = Field(default_factory=list)
    source_alert_ids: list[str] = Field(default_factory=list)

    @property
    def dimensions_resolved(self) -> int:
        return sum(1 for d in (self.identities, self.assets, self.cloud, self.business, self.threat) if d)

    @property
    def has_content(self) -> bool:
        return self.dimensions_resolved > 0


class ContextBundle(BaseModel):
    """Pre-fetched, structured context handed to every sub-agent."""

    bundle_id: UUID = Field(default_factory=uuid4)
    incident_id: UUID
    tenant_id: str = "default"
    alert_summary: str = ""

    # Discovered entities + per-entity context, keyed by ``EntityRef.key``.
    entities: list[EntityRef] = Field(default_factory=list)
    entity_neighborhoods: dict[str, EntityNeighborhood] = Field(default_factory=dict)
    peer_baselines: dict[str, UEBABaseline] = Field(default_factory=dict)
    threat_intel: dict[str, ThreatIntelMatch] = Field(default_factory=dict)
    incident_context: IncidentContextDimensions = Field(default_factory=IncidentContextDimensions)
    attack_context: dict[str, Any] = Field(default_factory=dict)

    # Memory (institutional tier) recall.
    historical_similar_cases: list[HistoricalCase] = Field(default_factory=list)

    # Provenance / health.
    build_started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    build_completed_at: datetime | None = None
    build_latency_ms: int = 0
    sources_called: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    depth: int = 2

    @property
    def is_complete(self) -> bool:
        """True when at least one source returned data and there are no errors."""
        return self.build_completed_at is not None and not self.errors

    @property
    def has_any_context(self) -> bool:
        """True when *any* slot in the bundle has actual content.

        Used by sub-agents to decide whether to short-circuit to the
        bundle-aware prompt or fall back to bare-alert reasoning.
        """
        return bool(
            self.entity_neighborhoods
            or self.peer_baselines
            or self.threat_intel
            or self.historical_similar_cases
            or self.incident_context.has_content
            or self.attack_context
        )

    def prompt_context_lines(self) -> list[str]:
        """Render the bundle's safe summary fields as prompt-ready lines.

        Sub-agents call this to inject pre-fetched context (entity
        neighbourhood, historical verdicts, UEBA deviation, TI matches)
        instead of re-discovering the same facts via primary tool calls.
        Only fields enumerated by ``summary_for_llm`` are surfaced — never
        raw OCSF or log payloads.
        """
        # A bundle with no content but a failed context lookup still has
        # something to say. Returning [] here meant the one case worth
        # warning about — we tried to resolve identity, asset and business
        # context and could not — reached the model as silence, which reads
        # the same as "this alert has no context".
        if not self.has_any_context and not self.incident_context.partial and not self.errors:
            return []
        s = self.summary_for_llm()
        parts: list[str] = ["", "Pre-fetched investigation context (ContextBundle):"]
        # Keep the exact bounded chain/graph summary early enough that the
        # existing overall prompt append bound does not hide it behind other
        # dimensions. Full source results stay in the Run's artifacts.
        if s.get("attack_context_summary"):
            parts.append(s["attack_context_summary"])
        if self.errors:
            parts.append("- Context lookups were partial or unavailable: " + ", ".join(self.errors[:10])
                         + ". Missing evidence is unknown, not proof of no relationships, activity or risk.")
        if s.get("entity_count"):
            parts.append(f"- Entities resolved: {s['entity_count']} ({', '.join(s.get('entity_types') or []) or 'unknown'})")
        if s.get("neighborhood_summaries"):
            parts.append("- Graph neighbourhood:")
            for line in s["neighborhood_summaries"]:
                parts.append(f"    * {line}")
        if s.get("blast_radius_max"):
            parts.append(f"- Max blast-radius score: {s['blast_radius_max']:.2f}")
        if s.get("historical_similar_count"):
            top = max(
                (h["similarity"] for h in s.get("historical_verdicts") or []),
                default=0.0,
            )
            parts.append(f"- Similar historical cases: {s['historical_similar_count']} (top similarity={top:.2f})")
            for h in (s.get("historical_verdicts") or [])[:3]:
                parts.append(f"    * {h['key']} → {h['verdict']} (sim={h['similarity']:.2f})")
        if s.get("ueba_entities_with_baseline"):
            deviation = s.get("ueba_max_deviation")
            parts.append(
                f"- UEBA: {s['ueba_entities_with_baseline']} entities with baseline, max deviation="
                + (f"{deviation:.2f}" if deviation is not None else "unknown (not supplied by source)")
            )
        if s.get("threat_intel_match_count"):
            parts.append(
                f"- Threat-intel matches: {s['threat_intel_match_count']} "
                f"(high-risk IOCs: {', '.join(s.get('threat_intel_high_risk_iocs') or []) or 'none'})"
            )

        # Identity, asset, cloud, business and threat depth. Rendered last
        # and rendered verbatim: the API composes these lines, and
        # re-summarising them here would drop the qualifiers that keep them
        # honest — an unconfirmed attribution, a partial lookup, a departed
        # employee whose account is still live.
        ctx = self.incident_context
        if ctx.narrative:
            parts.append("- Entity context:")
            parts.extend(f"    {line}" for line in ctx.narrative)
        elif ctx.partial:
            # No content *and* a failed lookup. Saying nothing here would
            # let the model read absence of context as absence of risk.
            parts.append(
                "- Entity context: unavailable (" + ", ".join(ctx.errors) + "). Treat missing identity/asset/business context as unknown, "
                "not as benign."
            )

        return parts

    def summary_for_llm(self) -> dict[str, Any]:
        """Pre-digested, contract-safe summary for LLM prompts.

        Every key returned here is on ``LLM_SAFE_KEYS`` and contains either
        a scalar, a small list of scalars, or a list of short string summaries
        — never raw OCSF / log payloads. ``LLMInputContract`` (T2.3) treats
        the output of this method as the canonical safe shape.
        """
        neigh_summaries = [
            f"{key}: {nbr.node_count} nodes (depth={nbr.depth})"
            + (f", blast_radius={nbr.blast_radius_score:.2f}" if nbr.blast_radius_score is not None else "")
            for key, nbr in sorted(self.entity_neighborhoods.items())
        ]
        blast_scores = [n.blast_radius_score for n in self.entity_neighborhoods.values() if n.blast_radius_score is not None]
        ueba_devs = [b.deviation_score for b in self.peer_baselines.values() if b.deviation_score is not None]
        high_risk = sorted(ti.ioc for ti in self.threat_intel.values() if ti.risk == "high")
        ti_sources: set[str] = set()
        for ti in self.threat_intel.values():
            ti_sources.update(ti.sources)
        return {
            "incident_id": str(self.incident_id),
            "alert_summary": self.alert_summary,
            "entity_count": len(self.entities),
            "entity_types": sorted({e.type for e in self.entities}),
            "entity_keys": sorted(e.key for e in self.entities)[:25],
            "neighborhood_summaries": neigh_summaries[:25],
            "blast_radius_max": max(blast_scores) if blast_scores else 0.0,
            "historical_similar_count": len(self.historical_similar_cases),
            "historical_verdicts": [
                {
                    "key": h.key,
                    "verdict": h.verdict,
                    "similarity": round(h.similarity_score, 3),
                }
                for h in self.historical_similar_cases[:10]
            ],
            "ueba_max_deviation": max(ueba_devs) if ueba_devs else None,
            "ueba_entities_with_baseline": len(self.peer_baselines),
            "threat_intel_high_risk_iocs": high_risk[:20],
            "threat_intel_match_count": len(self.threat_intel),
            "threat_intel_sources": sorted(ti_sources)[:20],
            "build_latency_ms": self.build_latency_ms,
            "sources_called": sorted(self.sources_called),
            "errors": self.errors[:5],
            "attack_context_summary": str(self.attack_context.get("model_summary") or ""),
        }


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def _ti_risk_from_enrichment(payload: dict[str, Any]) -> str:
    """Best-effort risk-bucket extraction from the enrichment service payload."""
    if not isinstance(payload, dict) or payload.get("error"):
        return "unknown"
    score = payload.get("risk_score") or payload.get("score") or 0.0
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.0
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    if score > 0:
        return "low"
    explicit = payload.get("risk") or payload.get("severity")
    if isinstance(explicit, str) and explicit.lower() in {"low", "medium", "high"}:
        return explicit.lower()
    return "unknown"


def _ti_sources(payload: dict[str, Any]) -> list[str]:
    if not isinstance(payload, dict):
        return []
    sources = payload.get("sources") or payload.get("providers") or []
    if isinstance(sources, list):
        return [str(s) for s in sources][:10]
    if isinstance(sources, dict):
        return sorted(sources.keys())[:10]
    return []


class ContextBundleBuilder:
    """Builds a :class:`ContextBundle` for an investigation in parallel.

    The builder is constructed with timeouts/limits — it never raises, only
    appends to ``bundle.errors`` if a context source misbehaves. Sub-agent
    code paths therefore stay deterministic regardless of substrate health.
    """

    DEFAULT_DEPTH = 2

    def __init__(
        self,
        *,
        depth: int | None = None,
        max_neighborhood_nodes: int = 30,
        history_limit: int = 5,
        ti_concurrency: int = 8,
        per_source_timeout: float = 3.5,
        api_token: str | None = None,
    ) -> None:
        self.depth = depth if depth is not None else int(os.getenv("AISOC_CONTEXT_BUNDLE_DEPTH", str(self.DEFAULT_DEPTH)))
        self.max_neighborhood_nodes = max_neighborhood_nodes
        self.history_limit = history_limit
        self.ti_concurrency = ti_concurrency
        self.per_source_timeout = per_source_timeout
        self.api_token = api_token

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def build(self, state: Any) -> ContextBundle:
        """Construct a bundle for the given ``InvestigationState``.

        ``state`` is typed as ``Any`` so this module doesn't import the
        heavyweight ``InvestigationState`` at module-load time and so a
        thin dict can be passed in tests.
        """
        t0 = time.monotonic()
        incident_id = getattr(state, "incident_id", None) or uuid4()
        tenant_id = str(getattr(state, "tenant_id", "default"))
        alert_summary = getattr(state, "alert_summary", "") or ""
        raw_alert = getattr(state, "raw_alert", {}) or {}
        from app.context.attack_context import enabled as attack_context_enabled, fetch_attack_context, model_summary, _unavailable

        attack_requested = attack_context_enabled()
        case_id = getattr(state, "case_id", None)
        alert_id = getattr(state, "alert_id", None)

        bundle = ContextBundle(
            incident_id=incident_id,
            tenant_id=tenant_id,
            alert_summary=alert_summary,
            depth=self.depth,
        )

        bundle.entities = extract_entities(raw_alert, summary=alert_summary)

        # Fan out — every coroutine is wrapped in ``_safe`` so a single
        # exception can't poison the bundle.
        results = await asyncio.gather(
            self._safe(
                "graph",
                self._fetch_neighborhoods(bundle.entities, tenant_id=tenant_id, errors=bundle.errors),
                bundle,
            ),
            self._safe(
                "memory",
                self._fetch_history(tenant_id, raw_alert, alert_summary),
                bundle,
            ),
            self._safe(
                "ueba",
                self._fetch_baselines(tenant_id, bundle.entities, errors=bundle.errors),
                bundle,
            ),
            self._safe(
                "threat_intel",
                self._fetch_threat_intel(bundle.entities),
                bundle,
            ),
            self._safe(
                "incident_context",
                self._fetch_incident_context(tenant_id, raw_alert),
                bundle,
            ),
            # Preparation belongs to the broker/Case entry. Preserve the
            # existing attack-context cutoff; other sources retain theirs.
            *([self._safe("attack_context", fetch_attack_context(
                tenant_id, case_id=case_id, alert_id=alert_id,
            ), bundle, timeout=22.0)] if attack_requested else []),
            return_exceptions=False,
        )

        neigh_result, history_result, ueba_result, ti_result, ctx_result = results[:5]
        if attack_requested:
            bundle.attack_context = (results[5] if isinstance(results[5], dict)
                                     else _unavailable(tenant_id, case_id, alert_id, "attack_context_lookup_unavailable"))
            preparation = raw_alert.get("attack_context_preparation")
            same_tenant = isinstance(preparation, dict) and str(preparation.get("tenant_id")) == tenant_id
            case_prepared = same_tenant and case_id and str(preparation.get("case_id")) == str(case_id)
            alert_prepared = (same_tenant and alert_id and preparation.get("scope") == "alert"
                              and str(preparation.get("alert_id")) == str(alert_id)
                              and preparation.get("owner") == "kafka_consumer")
            if case_prepared or alert_prepared:
                # Preserve entry preparation independently of GET query facts.
                owner = "kafka_consumer" if preparation.get("owner") == "kafka_consumer" else "case_api"
                bundle.attack_context["prepare"] = {**deepcopy(preparation), "owner": owner}
                bundle.attack_context["model_summary"] = model_summary(bundle.attack_context)
            for name in ("attack_chain", "attack_path", "alert_graph"):
                part = bundle.attack_context.get(name) or {}
                if part.get("status") in {"unavailable", "error"}:
                    bundle.errors.append(f"attack_context:{name}:{part.get('error') or 'unavailable'}")
        if isinstance(neigh_result, dict):
            bundle.entity_neighborhoods = neigh_result
        if isinstance(history_result, list):
            bundle.historical_similar_cases = history_result
        if isinstance(ueba_result, dict):
            bundle.peer_baselines = ueba_result
        if isinstance(ti_result, dict):
            bundle.threat_intel = ti_result
        if isinstance(ctx_result, IncidentContextDimensions):
            bundle.incident_context = ctx_result
            if ctx_result.partial:
                bundle.errors.extend("incident_context:" + reason for reason in (ctx_result.errors or ["partial"]))
        linked = raw_alert.get("alerts")
        if isinstance(linked, list) and len(linked) > _CASE_ALERT_LIMIT:
            bundle.errors.append(f"case_alert_scope:first_{_CASE_ALERT_LIMIT}_of_{len(linked)}")

        bundle.build_completed_at = datetime.now(UTC)
        bundle.build_latency_ms = int((time.monotonic() - t0) * 1000)
        return bundle

    # ------------------------------------------------------------------
    # Source fetchers — each returns its own slice of the bundle
    # ------------------------------------------------------------------

    async def _fetch_neighborhoods(
        self, entities: list[EntityRef], *, tenant_id: str | None = None,
        errors: list[str] | None = None,
    ) -> dict[str, EntityNeighborhood]:
        """Walk the graph for each principal entity, depth-N."""
        # Lazy import so ``services/agents`` modules without the API tool
        # installed (e.g. eval harness) can still import this builder.
        try:
            from app.tools.graph import get_blast_radius, get_entity_neighbors
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"graph tool unavailable: {exc}") from exc

        # Only walk principal entities — IPs, domains, hashes are TI input,
        # not graph principals.
        principals = [e for e in entities if e.type in ("host", "user", "email")]
        errors = errors if errors is not None else []
        if not principals:
            self._record_source("graph")
            return {}

        async def _walk(entity: EntityRef) -> tuple[str, EntityNeighborhood] | None:
            nbr_payload, blast_payload = await asyncio.gather(
                get_entity_neighbors(entity.type, entity.value, api_token=self.api_token, tenant_id=tenant_id),
                get_blast_radius(entity.type, entity.value, api_token=self.api_token, hops=self.depth, tenant_id=tenant_id),
                return_exceptions=True,
            )
            def failure(payload: Any) -> str | None:
                if isinstance(payload, BaseException):
                    return type(payload).__name__
                if not isinstance(payload, dict):
                    return "invalid_response"
                if payload.get("available") is False:
                    return "unavailable"
                if payload.get("error"):
                    return "error"
                return None

            nbr_error, blast_error = failure(nbr_payload), failure(blast_payload)
            if not nbr_error and (not isinstance(nbr_payload.get("neighbors"), list)
                                  or not all(isinstance(node, dict) for node in nbr_payload["neighbors"])
                                  or not isinstance(nbr_payload.get("edges", []), list)):
                nbr_error = "invalid_response"
            if nbr_error:
                errors.append(f"graph:{entity.key}:neighbors:{nbr_error}")
            if blast_error:
                errors.append(f"graph:{entity.key}:blast_radius:{blast_error}")
            # An unavailable query is not a successful empty neighbourhood.
            if nbr_error:
                return None
            nodes = nbr_payload["neighbors"]
            edges = nbr_payload.get("edges", [])
            blast = None
            if not blast_error:
                candidate = blast_payload.get("blast_radius_score")
                if type(candidate) in (int, float) and math.isfinite(candidate):
                    blast = float(candidate)
                else:
                    errors.append(f"graph:{entity.key}:blast_radius:invalid_response")
            summary = f"{len(nodes)} neighbors at depth {self.depth}" + (f", blast_radius={float(blast):.2f}" if blast is not None else "")
            return entity.key, EntityNeighborhood(
                entity=entity,
                depth=self.depth,
                nodes=nodes[: self.max_neighborhood_nodes],
                edges=edges[: self.max_neighborhood_nodes],
                blast_radius_score=float(blast) if blast is not None else None,
                summary=summary,
            )

        out: dict[str, EntityNeighborhood] = {}
        results = await asyncio.gather(*[_walk(e) for e in principals], return_exceptions=True)
        for r in results:
            # BaseException, not Exception: `gather(return_exceptions=True)`
            # hands back a cancelled child's `CancelledError`, which is a
            # BaseException on 3.8+. Filtering on `Exception` let it through
            # to the unpack below, turning a cancelled graph walk into
            # `TypeError: cannot unpack non-sequence CancelledError`.
            if isinstance(r, BaseException):
                logger.debug("context.neighborhood.failed", error=str(r))
                errors.append(f"graph:{type(r).__name__}")
                continue
            if r is None:
                continue
            key, nbr = r
            out[key] = nbr
        self._record_source("graph")
        return out

    async def _fetch_history(
        self,
        tenant_id: str,
        raw_alert: dict[str, Any],
        alert_summary: str,
    ) -> list[HistoricalCase]:
        """Pull similar-case verdicts from the institutional memory tier."""
        try:
            from app.memory.institutional import institutional_search
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"institutional memory unavailable: {exc}") from exc

        # Tag candidates: template_id, response_class, severity, plus a small
        # set of category tokens derived from the summary. Memory is queried
        # by tag so this is best-effort but fully deterministic for tests.
        tags: list[str] = []
        for k in ("template_id", "response_class", "category", "severity"):
            v = raw_alert.get(k)
            if isinstance(v, str) and v:
                tags.append(v)

        rows = await institutional_search(tenant_id, tags=tags or None, limit=self.history_limit, strict=True)

        own_set = {t.lower() for t in tags}
        out: list[HistoricalCase] = []
        for row in rows or []:
            value = row.get("value") if isinstance(row, dict) else {}
            if not isinstance(value, dict):
                value = {}
            row_tags = {str(t).lower() for t in (row.get("tags") or [])}
            jaccard = len(own_set & row_tags) / max(1, len(own_set | row_tags)) if own_set or row_tags else 0.0
            out.append(
                HistoricalCase(
                    key=str(row.get("key", "")),
                    verdict=str(value.get("verdict", "unknown")),
                    confidence=float(value.get("confidence", 0.0) or 0.0),
                    template_id=value.get("template_id"),
                    response_class=value.get("response_class"),
                    similarity_score=round(jaccard, 4),
                    rationale=(value.get("rationale") or value.get("summary") or None),
                    closed_at=row.get("created_at"),
                )
            )
        # Sort by similarity desc so the head of the list is most-relevant.
        out.sort(key=lambda h: h.similarity_score, reverse=True)
        self._record_source("memory")
        return out[: self.history_limit]

    async def _fetch_baselines(
        self,
        tenant_id: str,
        entities: list[EntityRef],
        *,
        errors: list[str] | None = None,
    ) -> dict[str, UEBABaseline]:
        """Pull per-entity UEBA baselines from the UEBA service."""
        ueba_url = os.getenv("AISOC_UEBA_URL", "http://ueba:8004")
        token = os.getenv("AISOC_UEBA_SERVICE_TOKEN", "").strip() or os.getenv("AISOC_SERVICE_TOKEN", "").strip()
        headers = {"X-AiSOC-Tenant-ID": tenant_id}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        principals = [e for e in entities if e.type in ("user", "email", "host", "ip")]
        if not principals:
            self._record_source("ueba")
            return {}

        out: dict[str, UEBABaseline] = {}
        errors = errors if errors is not None else []

        async with httpx.AsyncClient(timeout=self.per_source_timeout) as client:

            async def _one(entity: EntityRef) -> tuple[str, UEBABaseline] | None:
                # The UEBA list endpoint takes tenant + entity_type, then we
                # filter client-side. We accept that this is over-fetching
                # for now; the bundle is still bounded by ``history_limit``.
                try:
                    resp = await client.get(
                        f"{ueba_url}/api/v1/ueba/baselines",
                        params={"tenant_id": tenant_id, "entity_type": {"host": "device", "email": "user"}.get(entity.type, entity.type), "limit": 50},
                        headers=headers,
                    )
                    resp.raise_for_status()
                    rows = resp.json()
                    if not isinstance(rows, list):
                        raise ValueError("Invalid UEBA response")
                except Exception as exc:  # noqa: BLE001
                    logger.debug("context.ueba.failed", entity=entity.key, error=str(exc))
                    errors.append(f"ueba:{entity.key}:{type(exc).__name__}")
                    return None
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    if row.get("entity_id") != entity.value:
                        continue
                    window_days = row.get("window_days")
                    if window_days is None and row.get("window_start") and row.get("window_end"):
                        start = datetime.fromisoformat(str(row["window_start"]).replace("Z", "+00:00"))
                        end = datetime.fromisoformat(str(row["window_end"]).replace("Z", "+00:00"))
                        window_days = (end - start).days
                    deviation = row.get("deviation_score")
                    return entity.key, UEBABaseline(
                        entity=entity,
                        peer_group_id=row.get("peer_group_id"),
                        activity_window_days=int(window_days) if window_days is not None else 30,
                        baseline=row.get("feature_stats", row.get("baseline_features", {})) or {},
                        deviation_score=float(deviation) if deviation is not None else None,
                        notes=str(row.get("notes", "")),
                    )
                return None

            results = await asyncio.gather(*[_one(e) for e in principals], return_exceptions=True)
            for r in results:
                # See `_fetch_neighborhoods`: a cancelled child returns a
                # `CancelledError`, which is not an `Exception`.
                if isinstance(r, BaseException):
                    errors.append(f"ueba:{type(r).__name__}")
                    continue
                if r is None:
                    continue
                key, baseline = r
                out[key] = baseline
        self._record_source("ueba")
        return out

    async def _fetch_incident_context(
        self,
        tenant_id: str,
        raw_alert: dict[str, Any],
    ) -> IncidentContextDimensions:
        """Resolve the alert into identity, asset, cloud, business and threat.

        Delegated to the API rather than queried here: the API owns the Neo4j
        session and the tenant-scoping predicate, and duplicating a Cypher
        traversal whose correctness is a security property in a second
        service is how the two drift apart.
        """
        alert_ids: list[str] = []
        direct_id = raw_alert.get("id") or raw_alert.get("alert_id") or raw_alert.get("external_id")
        linked = raw_alert.get("alerts")
        candidates = ([direct_id] if direct_id else []) + (
            [row.get("id") for row in linked[:_CASE_ALERT_LIMIT] if isinstance(row, dict)]
            if isinstance(linked, list) else []
        )
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip() and candidate not in alert_ids:
                alert_ids.append(candidate)
        if not alert_ids:
            self._record_source("incident_context")
            return IncidentContextDimensions()
        if not self.api_token:
            raise RuntimeError("tenant_context_credential_unavailable")

        api_url = (os.getenv("AISOC_API_URL") or os.getenv("API_SERVICE_URL") or "http://api:8000").rstrip("/")
        headers = {"X-Tenant-ID": tenant_id, "Authorization": f"Bearer {self.api_token}"}
        dimensions = ("identities", "assets", "cloud", "business", "threat")
        merged = IncidentContextDimensions()
        if isinstance(linked, list) and len(linked) > _CASE_ALERT_LIMIT:
            merged.partial = True
            merged.errors.append(f"case_alert_scope:first_{_CASE_ALERT_LIMIT}_of_{len(linked)}")
        async with httpx.AsyncClient(timeout=self.per_source_timeout) as client:
            async def read(alert_id: str) -> dict[str, Any]:
                response = await client.get(f"{api_url}/api/v1/graph/incident-context/{alert_id}", headers=headers)
                response.raise_for_status()
                payload = response.json()
                if (not isinstance(payload, dict) or payload.get("tenant_id") != tenant_id
                        or payload.get("alert_id") != alert_id or payload.get("available") is False
                        or payload.get("error")
                        or any(not isinstance(payload.get(key), list)
                               or not all(isinstance(row, dict) for row in payload[key]) for key in dimensions)
                        or not isinstance(payload.get("narrative"), list)
                        or not all(isinstance(line, str) for line in payload["narrative"])
                        or type(payload.get("partial")) is not bool
                        or not isinstance(payload.get("errors"), list)
                        or not all(isinstance(reason, str) for reason in payload["errors"])):
                    raise ValueError("Invalid incident context identity or response")
                return payload

            results = await asyncio.gather(*(read(alert_id) for alert_id in alert_ids[:_CASE_ALERT_LIMIT]), return_exceptions=True)
        for alert_id, payload in zip(alert_ids, results):
            if isinstance(payload, BaseException):
                merged.partial = True
                merged.errors.append(f"alert:{alert_id}:{type(payload).__name__}")
                continue
            merged.source_alert_ids.append(alert_id)
            for key in dimensions:
                rows = getattr(merged, key)
                rows.extend(row for row in payload[key] if row not in rows)
            if payload["narrative"]:
                merged.narrative.append(f"Source alert {alert_id}:")
                merged.narrative.extend(payload["narrative"])
            if payload["partial"] or payload["errors"]:
                merged.partial = True
                merged.errors.extend(f"alert:{alert_id}:{reason}" for reason in (payload["errors"] or ["partial"]))
        if len(alert_ids) > _CASE_ALERT_LIMIT:
            merged.partial = True
            merged.errors.append(f"alert_scope:first_{_CASE_ALERT_LIMIT}_of_{len(alert_ids)}")
        self._record_source("incident_context")
        return merged

    async def _fetch_threat_intel(self, entities: list[EntityRef]) -> dict[str, ThreatIntelMatch]:
        """Bulk-enrich every IOC-shaped entity in the alert."""
        try:
            from app.tools.enrichment import bulk_enrich_iocs
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"enrichment tool unavailable: {exc}") from exc

        ioc_entities = [e for e in entities if e.type in ("ip", "domain", "hash", "url")]
        if not ioc_entities:
            self._record_source("threat_intel")
            return {}

        # Bulk endpoint takes a list of {value, ioc_type} — chunk so a single
        # giant alert can't fan out >1k items.
        batch = [{"value": e.value, "ioc_type": e.type} for e in ioc_entities[:64]]
        rows = await bulk_enrich_iocs(batch, raise_on_error=True)

        out: dict[str, ThreatIntelMatch] = {}
        for row in rows or []:
            if not isinstance(row, dict):
                raise ValueError("Invalid enrichment row")
            if row.get("error") or row.get("available") is False:
                raise RuntimeError("Enrichment source unavailable")
            value = row.get("value") or row.get("ioc")
            ioc_type = row.get("ioc_type") or row.get("type")
            if not value or not ioc_type:
                continue
            risk = _ti_risk_from_enrichment(row)
            out[f"{ioc_type}:{value}"] = ThreatIntelMatch(
                ioc=str(value),
                ioc_type=str(ioc_type),
                sources=_ti_sources(row),
                risk=risk,
                first_seen=row.get("first_seen"),
                last_seen=row.get("last_seen"),
                summary=str(row.get("summary") or row.get("description") or ""),
            )
        self._record_source("threat_intel")
        return out

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _safe(self, name: str, coro: Any, bundle: ContextBundle, *, timeout: float | None = None) -> Any:
        """Run ``coro`` with a per-source timeout; record errors instead of raising."""
        bundle.sources_called.append(name)
        try:
            return await asyncio.wait_for(coro, timeout=self.per_source_timeout if timeout is None else timeout)
        except TimeoutError:
            bundle.errors.append(f"{name}:timeout")
            return None
        except Exception as exc:  # noqa: BLE001
            bundle.errors.append(f"{name}:{type(exc).__name__}")
            logger.debug("context.source.failed", source=name, error=str(exc))
            return None

    def _record_source(self, name: str) -> None:
        # Sources are recorded on the bundle by the caller via the safe-wrap;
        # this method exists for future per-source instrumentation hooks.
        pass


# Module-level convenience for callers that just want a one-shot build.
async def build_context_bundle(state: Any, **kwargs: Any) -> ContextBundle:
    """Build a :class:`ContextBundle` for the given investigation state."""
    builder = ContextBundleBuilder(**kwargs)
    bundle = await builder.build(state)
    return bundle
