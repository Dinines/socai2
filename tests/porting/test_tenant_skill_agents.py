"""3A-05 typed skill reads and the literal guidance adopted by the real worker."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.agents.auto_triage_agent import _build_alert_context
from app.context import tenant_skills as ts
from app.models.state import InvestigationState
from app.replay.shadow import ContextSnapshot, FrozenTriageContextReader
from app.workers.fused_alert_consumer import FusedAlertTriageWorker, build_state
from app.workers.triage_persistence import CONTEXT_FREEZE_KINDS, LiveTriageContextReader, TriageContextReader

TENANT = "11111111-1111-1111-1111-111111111111"
OTHER = "22222222-2222-2222-2222-222222222222"
NOW = datetime(2026, 10, 20, 12, tzinfo=UTC)


def row(skill_id="skill-a", **changes):
    result = {
        "skill_id": skill_id, "version": 3, "activated_at": "2026-10-01T00:00:00Z",
        "expires_at": "2026-11-01T00:00:00Z",
        "body": {"id": skill_id, "name": "A controlled skill", "owner": "analyst@example.invalid",
                 "plan": ["Check process ancestry"], "expected_pivots": ["process_tree"], "min_pivots": 1,
                 "match": {"techniques": ["T1059"], "rule_ids": [], "sources": [], "keywords": []},
                 "guidance": "Collect ancestry before judging", "verdict_guidance": "Do not close without evidence",
                 "required_evidence": ["Process ancestry"], "escalate_when": ["Evidence is incomplete"]},
    }
    result.update(changes)
    return result


@pytest.fixture
def context(monkeypatch, tmp_path):
    keys = tmp_path / "skill-keys.json"
    keys.write_text(json.dumps({TENANT: "tenant-a-skill-key", OTHER: "tenant-b-skill-key"}))
    keys.chmod(0o600)
    monkeypatch.setenv("AISOC_TENANT_SKILLS_KEYS_FILE", str(keys))
    monkeypatch.setenv("AISOC_TENANT_SKILLS_ENABLED", "1")
    monkeypatch.setenv("AISOC_AGENTS_SERVICE_TOKEN", "must-never-use-shared")
    monkeypatch.setenv("AISOC_SERVICE_TOKEN", "must-never-use-fallback")
    monkeypatch.setenv("AISOC_ORG_MEMORY_KEYS_FILE", str(keys))
    monkeypatch.setattr(ts, "_now", lambda: NOW)
    ts.clear_cache()
    calls = []
    reply = SimpleNamespace(status=200, body={"tenant_id": TENANT, "skills": []}, error=None)

    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def get(self, url, **kwargs):
            calls.append((url, kwargs))
            if reply.error:
                raise reply.error
            return ts.httpx.Response(reply.status, content=json.dumps(reply.body).encode(), headers={'content-type': 'application/json'})
    monkeypatch.setattr(ts.httpx, "AsyncClient", lambda **kwargs: Client())
    yield keys, calls, reply
    ts.clear_cache()


@pytest.mark.asyncio
async def test_dedicated_bearer_identity_and_empty_read(context):
    _, calls, _ = context
    result = await LiveTriageContextReader().fetch_tenant_skills(TENANT)
    assert result["status"] == "no_match" and result["valid_count"] == 0
    assert result["source"] == "api.tenant-skills.resolved.active" and result["http_status"] == 200
    assert calls[0][1] == {"params": {"tenant_id": TENANT}, "headers": {"Authorization": "Bearer tenant-a-skill-key"}}
    assert "must-never" not in json.dumps(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["absent", "bad_json", "permissions", "unmapped", "symlink"])
async def test_missing_mapping_never_falls_back(context, monkeypatch, tmp_path, mode):
    keys, calls, _ = context
    if mode == "absent": monkeypatch.delenv("AISOC_TENANT_SKILLS_KEYS_FILE")
    elif mode == "bad_json": keys.write_text("{")
    elif mode == "permissions": keys.chmod(0o644)
    elif mode == "unmapped": keys.write_text("{}")
    else:
        link = tmp_path / "link.json"; link.symlink_to(keys)
        monkeypatch.setenv("AISOC_TENANT_SKILLS_KEYS_FILE", str(link))
    result = await ts.fetch_tenant_skills(TENANT)
    assert result["status"] == "unavailable" and result["reason"] == "not_configured"
    assert result["skills"] == [] and calls == []


@pytest.mark.asyncio
async def test_disabled_and_missing_tenant_are_distinct(context, monkeypatch):
    _, calls, _ = context
    assert (await ts.fetch_tenant_skills(None))["reason"] == "missing_tenant"
    monkeypatch.setenv("AISOC_TENANT_SKILLS_ENABLED", "0")
    assert (await ts.fetch_tenant_skills(TENANT))["status"] == "disabled" and calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status,reason", [(401, "auth_failed"), (403, "auth_failed"), (500, "http_error"), (302, "http_error")])
async def test_http_failure_is_not_no_match(context, status, reason):
    _, _, reply = context; reply.status = status
    result = await ts.fetch_tenant_skills(TENANT)
    assert result["status"] == "unavailable" and result["reason"] == reason
    assert result["http_status"] == status and result["skills"] == []


@pytest.mark.asyncio
async def test_transport_failure_adopts_nothing(context):
    _, _, reply = context; reply.error = ts.httpx.ConnectError("private location not logged")
    result = await ts.fetch_tenant_skills(TENANT)
    assert result["status"] == "unavailable" and result["reason"] == "transport_error" and result["skills"] == []


def bad_payloads():
    invalid_min = row(); invalid_min["body"]["min_pivots"] = "invalid"
    nonfinite_min = row(); nonfinite_min["body"]["min_pivots"] = float("inf")
    missing_plan = row(); missing_plan["body"]["plan"] = []
    invalid_match = row(); invalid_match["body"]["match"] = "not a match"
    wrong_body_id = row(); wrong_body_id["body"]["id"] = "other"
    bad_guidance = row(); bad_guidance["body"]["guidance"] = ["wrong type"]
    return [None, {"tenant_id": OTHER, "skills": []}, {"tenant_id": TENANT},
            {"tenant_id": TENANT, "skills": ["bad"]},
            *[{"tenant_id": TENANT, "skills": [value]} for value in
              [row(version=0), row(version=True), row(version=1.5), row(expires_at="bad"), invalid_min, nonfinite_min, missing_plan, invalid_match, wrong_body_id, bad_guidance]],
            {"tenant_id": TENANT, "skills": [row(), row(version=4)]}]


@pytest.mark.asyncio
@pytest.mark.parametrize("body", bad_payloads())
async def test_invalid_response_never_poisoned_cache(context, body):
    _, _, reply = context; reply.body = body
    result = await ts.fetch_tenant_skills(TENANT)
    assert result["status"] == "unavailable" and result["reason"] == "invalid_response"
    assert result["skills"] == [] and ts._cache == {}


@pytest.mark.asyncio
async def test_expiry_rechecked_on_fresh_cache_and_detached_rows(context, monkeypatch):
    _, calls, reply = context; reply.body["skills"] = [row(expires_at=(NOW + timedelta(seconds=1)).isoformat())]
    first = await ts.fetch_tenant_skills(TENANT)
    first["skills"][0]["body"]["guidance"] = "mutated"
    second = await ts.fetch_tenant_skills(TENANT)
    assert second["skills"][0]["body"]["guidance"] != "mutated"
    monkeypatch.setattr(ts, "_now", lambda: NOW + timedelta(seconds=2))
    result = await ts.fetch_tenant_skills(TENANT)
    assert result["status"] == "no_match" and result["expired_count"] == 1
    assert result["cache"]["source"] == "memory" and result["skills"] == [] and len(calls) == 1


@pytest.mark.asyncio
async def test_failed_expired_refresh_never_adopts_stale_then_recovers(context, monkeypatch):
    _, _, reply = context; reply.body["skills"] = [row()]
    assert (await ts.fetch_tenant_skills(TENANT))["status"] == "success"
    monkeypatch.setattr(ts, "_CACHE_TTL_S", -1)
    reply.status = 403
    failed = await ts.fetch_tenant_skills(TENANT)
    assert failed["status"] == "unavailable" and failed["skills"] == [] and failed["cache"]["freshness"] == "expired"
    reply.status = 200
    assert (await ts.fetch_tenant_skills(TENANT))["status"] == "success"


@pytest.mark.asyncio
async def test_url_change_misses_previous_cache_and_compatibility_projection(context, monkeypatch):
    _, calls, reply = context; reply.body["skills"] = [row()]
    assert len(await ts.fetch_skills(TENANT)) == 1
    monkeypatch.setattr(ts, "_API_URL", "http://other-api")
    await ts.fetch_tenant_skills(TENANT)
    assert len(calls) == 2 and calls[-1][0].startswith("http://other-api/")


@pytest.mark.asyncio
async def test_rotation_removal_and_tenant_isolation(context):
    keys, calls, reply = context; reply.body["skills"] = [row()]
    await ts.fetch_tenant_skills(TENANT)
    reply.body = {"tenant_id": OTHER, "skills": [row("skill-b")]}
    second = await ts.fetch_tenant_skills(OTHER)
    assert second["skills"][0]["skill_id"] == "skill-b"
    assert calls[-1][1]["headers"]["Authorization"] == "Bearer tenant-b-skill-key"
    assert (await ts.fetch_tenant_skills(TENANT))["skills"][0]["skill_id"] == "skill-a"
    reply.body = {"tenant_id": TENANT, "skills": [row()]}
    keys.write_text(json.dumps({TENANT: "rotated"}))
    await ts.fetch_tenant_skills(TENANT)
    assert len(calls) == 3 and calls[-1][1]["headers"]["Authorization"] == "Bearer rotated"
    keys.write_text("{}")
    assert (await ts.fetch_tenant_skills(TENANT))["reason"] == "not_configured" and len(calls) == 3


@pytest.mark.asyncio
async def test_frozen_reader_never_uses_live_clock_or_network(context, monkeypatch):
    _, calls, _ = context
    split = datetime(2026, 1, 1, tzinfo=UTC)
    historical = row(expires_at="2026-02-01T00:00:00Z")
    candidate = row("candidate", activated_at="2026-10-01T00:00:00Z")
    snapshot = ContextSnapshot(split_at=split, skills=(historical,), skills_under_test=(candidate,))
    reader = FrozenTriageContextReader(snapshot)
    assert isinstance(reader, TriageContextReader)
    result = await reader.fetch_tenant_skills(TENANT)
    assert result["read_at"] == split.isoformat() and result["cache"]["freshness"] == "frozen"
    assert [x["skill_id"] for x in result["skills"]] == ["skill-a", "candidate"]
    result["skills"][0]["body"]["guidance"] = "mutated"
    assert (await reader.fetch_tenant_skills(TENANT))["skills"][0]["body"]["guidance"] != "mutated"
    assert CONTEXT_FREEZE_KINDS["fetch_tenant_skills"] == "snapshot" and reader.reads["fetch_tenant_skills"] == 2 and calls == []


def envelope():
    return {"tenant_id": TENANT, "id": OTHER, "alert": {"id": OTHER, "title": "Process ancestry absent",
            "source": "controlled-edr", "mitre_techniques": ["T1059.001"]}}


@pytest.mark.asyncio
@pytest.mark.parametrize("match,expected", [("techniques", "technique=T1059"), ("sources", "source=controlled-edr")])
async def test_real_build_state_retains_source_and_technique_selection(match, expected):
    candidate = row(); candidate["body"]["match"] = {match: ["T1059" if match == "techniques" else "controlled-edr"]}
    reader = FrozenTriageContextReader(ContextSnapshot(split_at=NOW, skills=(candidate,)))
    worker = FusedAlertTriageWorker(bootstrap_servers="", context_reader=reader)
    state = build_state(envelope())
    assert state is not None and state.raw_alert["source"] == "controlled-edr" and state.mitre_mappings == []
    await worker._attach_tenant_skill(state)
    assert state.tenant_skill["ref"] == "skill-a@v3"
    assert state.tenant_skill_read["selection"]["reasons"] == [expected]
    assert state.tenant_skill_read["selection"]["score"] == (10 if match == "techniques" else 5)


@pytest.mark.asyncio
async def test_read_success_without_selection_does_not_claim_no_tenant_skills():
    candidate = row(); candidate["body"]["match"] = {"techniques": ["T1566"]}
    reader = FrozenTriageContextReader(ContextSnapshot(split_at=NOW, skills=(candidate,)))
    worker = FusedAlertTriageWorker(bootstrap_servers="", context_reader=reader)
    state = build_state(envelope()); await worker._attach_tenant_skill(state)
    assert state.tenant_skill is None and state.tenant_skill_read["status"] == "success"
    assert state.tenant_skill_read["selection"]["status"] == "no_match"
    assert "within the returned candidate set" in _build_alert_context(state, nonce="test")


@pytest.mark.asyncio
async def test_long_guidance_literal_block_hash_and_no_second_truncation():
    candidate = row(); candidate["body"]["guidance"] = "A" * 2000
    candidate["body"]["verdict_guidance"] = "B" * 2000
    candidate["body"]["required_evidence"] = ["Evidence" * 100] * 10
    reader = FrozenTriageContextReader(ContextSnapshot(split_at=NOW, skills=(candidate,)))
    worker = FusedAlertTriageWorker(bootstrap_servers="", context_reader=reader)
    state = build_state(envelope()); await worker._attach_tenant_skill(state)
    read = state.tenant_skill_read; block = read["prompt_block"]
    assert len(block) > 2000 and len(block) < 2100 and block.endswith("…[truncated]")
    assert block == state.tenant_skill["triage_guidance"] and block in _build_alert_context(state, nonce="test")
    assert read["prompt_sha256"] == hashlib.sha256(block.encode()).hexdigest()


def test_no_read_and_candidate_limit_are_explicit():
    state = InvestigationState(tenant_id=UUID(TENANT), incident_id=UUID(OTHER))
    assert state.tenant_skill_read == {"status": "not_requested"}
    assert "Tenant skills read" not in _build_alert_context(state, nonce="test")
    read = ts.make_read(TENANT, rows=[row(f"skill-{i}") for i in range(51)])
    assert read["valid_count"] == 51 and read["candidate_count"] == 50 and read["truncated_count"] == 1
    assert len(read["skills"]) == 50 and "outside selection" in ts.render_read_status(read)


def test_additive_scoring_and_id_tie_breaks_keep_provenance():
    a, z = row("alpha"), row("zulu")
    selected, provenance = ts.select_skill_with_provenance([z, a], techniques=["T1059.001"])
    assert selected.skill_id == "alpha" and provenance["score"] == 10
    assert provenance["reasons"] == ["technique=T1059"]
    a["body"]["match"] = {"rule_ids": ["rule"], "techniques": ["T1059"], "sources": ["edr"], "keywords": ["process"]}
    selected, provenance = ts.select_skill_with_provenance([a], summary="process", techniques=["T1059.001"], rule_id="rule", source="edr")
    assert provenance["score"] == 37 and provenance["reasons"] == ["rule_id=rule", "technique=T1059", "source=edr", "keywords=process"]
