"""
Attack-Path Investigation Agent.

Runs after the standard investigation node. Walks the knowledge graph
(Case → Alerts → Hosts/Users → IOCs → MITRE techniques) and computes blast
radius for the highest-impact pivot points. Adds graph-derived findings and
proposed actions to the InvestigationState.

This is the Neo4j + LangGraph integration step: it converts the static
investigation report into a connected story that explains *how an attacker
could reach the crown jewels from the observed indicators*.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import structlog

from app.models.state import ActionRisk, AgentStatus, InvestigationState, ProposedAction
from app.tools.graph import get_attack_path, get_blast_radius
from app.context.attack_context import reader_token

logger = structlog.get_logger()

# Score thresholds (0.0–1.0) that mirror the buckets in graph_service.py.
_BLAST_HIGH = 0.7

# Cap how many entities we run blast-radius on per run to keep tail latency
# bounded — the graph traversal is the most expensive part of the workflow.
_MAX_BLAST_ENTITIES = 5


async def run_attack_path(state: InvestigationState) -> InvestigationState:
    """Walk the graph for the case linked to this investigation and enrich state."""
    logger.info("Attack-path agent starting", incident_id=str(state.incident_id))
    state.iteration_count += 1

    context = (state.context_bundle or {}).get("attack_context") or {}
    if context and context.get("scope") == "alert" and not context.get("case_id"):
        # An Alert neighborhood is useful scope context, but never a fabricated
        # Case path. Reuse the original API query's returned graph and score.
        part = context.get("alert_graph") or {}
        data = part.get("data") if isinstance(part.get("data"), dict) else {}
        state.threat_intel["alert_graph"] = {
            "alert_id": context.get("alert_id"), "status": part.get("status"),
            "source": part.get("source"), "error": part.get("error"),
            **data,
        }
        if part.get("status") in {"unavailable", "error"} or part.get("error"):
            state.add_finding(f"Alert graph lookup unavailable for {context.get('alert_id')} ({part.get('error') or part.get('status')}); graph scope remains unknown.")
        else:
            neighbors = data.get("neighbors") or {}
            blast = data.get("blast_radius") or {}
            blast = blast if isinstance(blast, dict) else {}
            rows = neighbors.get("neighbors", neighbors.get("nodes", [])) if isinstance(neighbors, dict) else []
            rows = rows if isinstance(rows, list) else []
            state.add_finding(f"Alert-associated graph scope for {context.get('alert_id')}: {len(rows)} neighboring nodes, {blast.get('total_affected', 'unknown')} reachable entities (source={part.get('source')}). This is not a Case attack path or confirmed attack progression.")
        return state

    case_id = context.get("case_id") if context else _resolve_case_id(state)
    if not case_id:
        # No case linkage yet — agent has nothing to traverse. Stay silent so
        # we don't pollute the report with noise; the workflow is still
        # complete because investigation_node already set status.
        logger.debug("No case_id on state; skipping attack-path agent")
        return state

    token = reader_token(str(state.tenant_id))
    if context:
        part = context.get("attack_path") or {}
        path = part.get("data") if isinstance(part.get("data"), dict) else {}
        if part.get("status") in {"unavailable", "error", "not_linked"}:
            state.threat_intel["attack_path"] = {"case_id": case_id, "status": part.get("status"), "source": part.get("source"), "error": part.get("error")}
            state.add_finding(f"Attack-path lookup unavailable for case {case_id} ({part.get('error') or part.get('status')}); the graph was not established as empty.")
            return state
        if part.get("error"):
            state.add_finding(f"Attack-path uses {part.get('source')} for case {case_id}; the primary graph lookup was unavailable ({part['error']}). Returned associations retain that source limitation.")
    else:
        path = await get_attack_path(case_id=case_id, api_token=token, tenant_id=str(state.tenant_id))
    if path.get("error") or path.get("available") is False:
        state.add_finding(f"Attack-path lookup unavailable for case {case_id} ({path.get('error') or 'source unavailable'}); graph scope remains unknown.")
        return state
    if not path.get("nodes"):
        state.add_finding(f"Attack-path graph empty for case {case_id} (node_count={path.get('node_count', 0)}).")
        return state

    # ---- Summarise the path ----
    nodes: list[dict[str, Any]] = path.get("nodes", [])
    edges: list[dict[str, Any]] = path.get("edges", [])
    label_counts = Counter(n.get("label", "Unknown") for n in nodes)
    state.add_finding(
        "Attack-path graph: "
        + ", ".join(f"{c} {label}" for label, c in label_counts.most_common())
        + f" across {len(edges)} relationships."
    )

    # Tactic chain (deduplicated, order-preserving) gives a quick read on
    # how far through the kill chain the attacker has progressed.
    tactic_chain = _extract_tactic_chain(nodes)
    if tactic_chain:
        state.add_finding(f"Associated MITRE tactic labels (not an observed attack sequence): {' → '.join(tactic_chain)}.")

    # ---- Pick high-value entities to compute blast radius for ----
    pivot_targets = _select_blast_targets(nodes)

    high_blast: list[dict[str, Any]] = []
    for pivot in pivot_targets[:_MAX_BLAST_ENTITIES]:
        blast = await get_blast_radius(
            entity_type=pivot["entity_type"],
            entity_id=pivot["entity_id"],
            api_token=token,
            tenant_id=str(state.tenant_id),
        )
        if blast.get("error"):
            continue
        score = float(blast.get("blast_radius_score", 0.0))
        if score >= _BLAST_HIGH:
            high_blast.append(
                {
                    **blast,
                    "label": pivot["label"],
                    "name": pivot.get("name", pivot["entity_id"]),
                    "entity_id": pivot["entity_id"],
                    "entity_type": pivot["entity_type"],
                }
            )

    if high_blast:
        for b in high_blast:
            state.add_finding(
                f"High blast radius from {b['label']} '{b['name']}': "
                f"{b['total_affected']} entities reachable "
                f"(score={b['blast_radius_score']:.2f}, "
                f"breakdown={dict(b.get('type_breakdown', {}))})."
            )

        # Propose an isolation action for the highest-scoring pivot.
        top = max(high_blast, key=lambda b: b["blast_radius_score"])
        if top["label"] in ("Host", "User"):
            state.proposed_actions.append(
                ProposedAction(
                    action_type=("isolate_host" if top["label"] == "Host" else "disable_user"),
                    description=(f"Isolate {top['label'].lower()} '{top['name']}' — {top['total_affected']} downstream entities at risk."),
                    risk_level=ActionRisk.HIGH,
                    target=top["name"],
                    requires_approval=True,
                    rationale=(f"Graph blast radius {top['blast_radius_score']:.2f} with {top['total_affected']} reachable entities."),
                    parameters={
                        "entity_type": top["entity_type"],
                        "entity_id": top["entity_id"],
                        "blast_radius_score": top["blast_radius_score"],
                    },
                )
            )

    # Persist a compact summary on the state so downstream services (UI,
    # report writer) can render it without re-querying the graph.
    state.threat_intel.setdefault("attack_path", {})
    state.threat_intel["attack_path"] = {
        "case_id": case_id,
        "source": (context.get("attack_path") or {}).get("source") if context else "legacy_graph_query",
        "node_count": path.get("node_count", len(nodes)),
        "edge_count": path.get("edge_count", len(edges)),
        "tactic_chain": tactic_chain,
        "label_counts": dict(label_counts),
        "high_blast_entities": [
            {
                "label": b["label"],
                "name": b["name"],
                "score": b["blast_radius_score"],
                "total_affected": b["total_affected"],
            }
            for b in high_blast
        ],
    }

    # Don't override a terminal status set by the previous node, but if the
    # workflow is still running, flag completion now.
    if state.status == AgentStatus.RUNNING:
        state.status = AgentStatus.COMPLETED

    logger.info(
        "Attack-path complete",
        case_id=case_id,
        node_count=len(nodes),
        edge_count=len(edges),
        high_blast=len(high_blast),
    )
    return state


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _resolve_case_id(state: InvestigationState) -> str | None:
    """Find the case id on the state, tolerant of where the orchestrator put it."""
    raw = state.raw_alert or {}
    return raw.get("case_id") or raw.get("caseId") or (state.threat_intel or {}).get("case_id")


def _extract_tactic_chain(nodes: list[dict[str, Any]]) -> list[str]:
    """Pull MITRE tactic names from Technique nodes, preserving first-seen order."""
    seen: list[str] = []
    for node in nodes:
        if node.get("label") != "Technique":
            continue
        props = node.get("properties", {}) or {}
        tactic = props.get("tactic_name") or props.get("tactic")
        if tactic and tactic not in seen:
            seen.append(tactic)
    return seen


def _select_blast_targets(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank Host/User/IOC nodes for blast-radius traversal.

    Hosts and users with high criticality / risk_score are evaluated first;
    IOCs are included as a tail because they're cheaper to score but rarely
    surface new pivot points the existing investigation hasn't already used.
    """
    candidates: list[tuple[float, dict[str, Any]]] = []
    for node in nodes:
        label = node.get("label")
        props = node.get("properties", {}) or {}
        nid = node.get("id") or props.get("id") or props.get("value")
        if not nid:
            continue

        if label == "Host":
            crit = (props.get("criticality") or "medium").lower()
            score = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.2}.get(crit, 0.5)
            candidates.append(
                (
                    score,
                    {
                        "entity_type": "host",
                        "entity_id": nid,
                        "label": "Host",
                        "name": props.get("hostname", nid),
                    },
                )
            )
        elif label == "User":
            risk = float(props.get("risk_score", 0.0) or 0.0)
            candidates.append(
                (
                    min(1.0, risk + 0.3),
                    {
                        "entity_type": "user",
                        "entity_id": nid,
                        "label": "User",
                        "name": props.get("username", nid),
                    },
                )
            )
        elif label == "IOC":
            candidates.append(
                (
                    0.2,
                    {
                        "entity_type": "ioc",
                        "entity_id": nid,
                        "label": "IOC",
                        "name": props.get("value", nid),
                    },
                )
            )

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [c[1] for c in candidates]
