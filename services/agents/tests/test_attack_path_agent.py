"""Tests for the Attack-Path Investigation Agent.

These tests do not require a live Neo4j or API service; they monkeypatch the
graph-tool calls so the agent can be exercised in isolation. The intent is to
lock down:

* findings / proposed_actions are populated only when the graph returns data
* tactic chain extraction preserves order and deduplicates
* high blast-radius hosts produce an isolation `ProposedAction`
* the agent stays silent when no `case_id` is on state (no false findings)
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest

_AGENTS_ROOT = Path(__file__).resolve().parents[1]
if str(_AGENTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENTS_ROOT))

# Imports must come after path mutation.
from app.agents import attack_path_agent  # noqa: E402
from app.models.state import (  # noqa: E402
    ActionRisk,
    AgentStatus,
    InvestigationState,
)


def _state(case_id: str | None = "case-123") -> InvestigationState:
    return InvestigationState(
        incident_id=uuid4(),
        tenant_id=uuid4(),
        alert_summary="EDR detection",
        raw_alert={"case_id": case_id} if case_id else {},
        status=AgentStatus.RUNNING,
    )


@pytest.mark.asyncio
async def test_attack_path_skipped_when_no_case_id(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"path": False, "blast": False}

    async def _fake_path(*_a, **_kw):
        called["path"] = True
        return {"nodes": [], "edges": []}

    async def _fake_blast(*_a, **_kw):
        called["blast"] = True
        return {}

    monkeypatch.setattr(attack_path_agent, "get_attack_path", _fake_path)
    monkeypatch.setattr(attack_path_agent, "get_blast_radius", _fake_blast)

    state = _state(case_id=None)
    result = await attack_path_agent.run_attack_path(state)

    assert called["path"] is False
    assert called["blast"] is False
    assert result.findings == []
    assert result.proposed_actions == []


@pytest.mark.asyncio
async def test_attack_path_records_summary_and_tactic_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes = [
        {"id": "case-123", "label": "Case", "properties": {}},
        {"id": "alert-1", "label": "Alert", "properties": {}},
        {
            "id": "host-1",
            "label": "Host",
            "properties": {"hostname": "web-01", "criticality": "high"},
        },
        {
            "id": "tech-T1059",
            "label": "Technique",
            "properties": {"tactic_name": "Execution"},
        },
        {
            "id": "tech-T1071",
            "label": "Technique",
            "properties": {"tactic_name": "C2"},
        },
        # Duplicate tactic should not appear twice in the chain.
        {
            "id": "tech-T1105",
            "label": "Technique",
            "properties": {"tactic_name": "C2"},
        },
    ]
    edges = [{"from": "case-123", "to": "alert-1", "type": "HAS_ALERT"}] * 5

    async def _fake_path(case_id: str, **_kw):
        assert case_id == "case-123"
        return {"nodes": nodes, "edges": edges, "node_count": 6, "edge_count": 5}

    async def _fake_blast(entity_type: str, entity_id: str, **_kw):
        # Only the high-criticality host should be queried first; return a
        # high-blast result for it.
        if entity_type == "host" and entity_id == "host-1":
            return {
                "blast_radius_score": 0.82,
                "total_affected": 17,
                "type_breakdown": {"User": 4, "IOC": 13},
                "affected_nodes": [],
            }
        return {"blast_radius_score": 0.1, "total_affected": 0, "type_breakdown": {}}

    monkeypatch.setattr(attack_path_agent, "get_attack_path", _fake_path)
    monkeypatch.setattr(attack_path_agent, "get_blast_radius", _fake_blast)

    state = _state()
    result = await attack_path_agent.run_attack_path(state)

    assert any("Attack-path graph" in f for f in result.findings)
    assert any("Associated MITRE tactic labels" in f for f in result.findings)
    assert any("High blast radius from Host 'web-01'" in f for f in result.findings)

    chain = result.threat_intel["attack_path"]["tactic_chain"]
    assert chain == ["Execution", "C2"], "duplicate tactics should be deduplicated in order"

    isolate_actions = [a for a in result.proposed_actions if a.action_type == "isolate_host"]
    assert len(isolate_actions) == 1
    action = isolate_actions[0]
    assert action.target == "web-01"
    assert action.risk_level == ActionRisk.HIGH
    assert action.requires_approval is True
    assert action.parameters["entity_type"] == "host"
    assert action.parameters["blast_radius_score"] == pytest.approx(0.82)


@pytest.mark.asyncio
async def test_attack_path_no_findings_for_empty_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_path(*_a, **_kw):
        return {"nodes": [], "edges": [], "node_count": 0, "edge_count": 0}

    async def _fake_blast(*_a, **_kw):
        # Should never be called when the graph is empty.
        raise AssertionError("blast radius queried for empty graph")

    monkeypatch.setattr(attack_path_agent, "get_attack_path", _fake_path)
    monkeypatch.setattr(attack_path_agent, "get_blast_radius", _fake_blast)

    state = _state()
    result = await attack_path_agent.run_attack_path(state)

    assert any("Attack-path graph empty" in f for f in result.findings)
    assert result.proposed_actions == []


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", ["case", "alert"])
async def test_attack_path_reuses_case_snapshot_without_query(monkeypatch, scope):
    async def unexpected(*_args, **_kwargs):
        raise AssertionError("prefetched Case path was queried again")

    monkeypatch.setattr(attack_path_agent, "get_attack_path", unexpected)
    monkeypatch.setattr(attack_path_agent, "get_blast_radius", unexpected)
    state = _state()
    state.context_bundle = {"attack_context": {
        "scope": scope, "case_id": "case-123",
        "attack_path": {"status": "success", "source": "relational_fallback", "error": "ServiceUnavailable",
                        "data": {"nodes": [{"id": "case-123", "label": "Case", "properties": {}}], "edges": []}},
    }}
    result = await attack_path_agent.run_attack_path(state)
    assert result.threat_intel["attack_path"]["source"] == "relational_fallback"
    assert any("Attack-path graph" in line for line in result.findings)
    assert any("primary graph lookup was unavailable" in line for line in result.findings)


@pytest.mark.asyncio
async def test_attack_path_reuses_alert_graph_without_fabricating_case(monkeypatch):
    async def unexpected(*_args, **_kwargs):
        raise AssertionError("prefetched Alert graph was queried again")

    monkeypatch.setattr(attack_path_agent, "get_attack_path", unexpected)
    monkeypatch.setattr(attack_path_agent, "get_blast_radius", unexpected)
    state = _state(case_id=None)
    state.context_bundle = {"attack_context": {
        "scope": "alert", "case_id": None, "alert_id": "alert-a",
        "attack_path": {"status": "not_linked", "data": None},
        "alert_graph": {"status": "success", "source": "neo4j", "error": None,
                        "data": {"neighbors": {"neighbors": [{"id": "host-a"}]}, "blast_radius": {"total_affected": 1, "blast_radius_score": 0.3}}},
    }}
    result = await attack_path_agent.run_attack_path(state)
    assert "attack_path" not in result.threat_intel
    assert result.threat_intel["alert_graph"]["alert_id"] == "alert-a"
    assert any("not a Case attack path" in line for line in result.findings)


@pytest.mark.asyncio
async def test_legacy_attack_path_failure_is_not_reported_as_empty(monkeypatch):
    state = _state()
    monkeypatch.setattr(attack_path_agent, "reader_token", lambda _tenant: "tenant-reader")

    async def unavailable(**kwargs):
        assert kwargs["api_token"] == "tenant-reader"
        assert kwargs["tenant_id"] == str(state.tenant_id)
        return {"available": False, "error": "reader unavailable", "nodes": []}

    monkeypatch.setattr(attack_path_agent, "get_attack_path", unavailable)
    result = await attack_path_agent.run_attack_path(state)
    assert any("lookup unavailable" in line for line in result.findings)
    assert not any("graph empty" in line for line in result.findings)
