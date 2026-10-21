"""B3 actual four node functions; HTTP and model boundary doubles only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest

from app.context import knowledge_base as kb
from app.investigator import forensic_agent, recon_agent, report_writer_agent, responder_agent
from app.investigator.knowledge_prompt import prefetch_knowledge
from app.investigator.knowledge_prompt import record_knowledge_citations, report_knowledge_references
from app.investigator.state import InvestigatorState

TENANT = "11111111-1111-1111-1111-111111111111"
RUN = "22222222-2222-2222-2222-222222222222"
CASE = "33333333-3333-3333-3333-333333333333"
NODES = (recon_agent, forensic_agent, responder_agent, report_writer_agent)


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    kb.clear_cache()
    monkeypatch.setenv("AISOC_TRIAGE_KB_ENABLED", "1")
    monkeypatch.delenv("AISOC_TRIAGE_KB_KEYS_FILE", raising=False)
    yield
    kb.clear_cache()


def source():
    fixture = json.loads((Path(__file__).parent / "fixtures/investigation-knowledge-b3.json").read_text())
    row = deepcopy(fixture["documents"][1])
    assert hashlib.sha256(row["content"].encode()).hexdigest() == row["provenance"]["content_sha256"]
    row.pop("provenance")
    return {**row, "created_at": "2026-10-20T00:00:00+00:00", "updated_at": "2026-10-20T00:00:00+00:00", "score": 0.8}


def api(monkeypatch, tmp_path, *, status=200, rows=None):
    keyfile = tmp_path / "kb-readers.json"
    keyfile.write_text(json.dumps({TENANT: "synthetic-kb-reader"}))
    keyfile.chmod(0o600)
    monkeypatch.setenv("AISOC_TRIAGE_KB_KEYS_FILE", str(keyfile))
    calls = []
    def handler(request):
        calls.append(request)
        assert request.headers["Authorization"] == "Bearer synthetic-kb-reader"
        assert request.url.params["tenant_id"] == TENANT
        assert request.url.params["q"] == "Password spraying"
        assert request.url.path.endswith("/kb/runbooks/for-triage")
        return httpx.Response(status, json={"tenant_id": TENANT, "as_of": None, "chunks": rows or [],
            "excluded_after_cutoff": 0, "excluded_after_update": 0, "excluded_after_cutoff_total": 0,
            "without_timestamp": 0})
    client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))
    return calls


def state():
    return InvestigatorState(run_id=UUID(RUN), case_id=CASE, tenant_id=TENANT,
        alert_summary="Case transport metadata with severity high and an unrelated identifier",
        raw_alert={"alerts": [{"title": "Password spraying", "description": "Marked synthetic observations; no attribution established."}]})


def models(monkeypatch, *, report_citation="[KB1]"):
    prompts = []
    contents = [
        json.dumps({"iocs": [], "mitre_techniques": [], "threat_actors": [], "summary": "Background guidance [KB1]."}),
        json.dumps({"timeline": [], "artefacts": [], "root_cause_hypothesis": "Possible spraying [KB1].",
                    "blast_radius": "Unknown", "confidence": 0.4, "summary": "Synthetic observation remains inconclusive."}),
        json.dumps({"recommended_actions": [], "containment_steps": [], "eradication_steps": [], "recovery_steps": [],
                    "estimated_effort_hours": 1.0, "risk_level": "medium", "summary": "Check failed login distribution [KB1]."}),
        f"# Marked investigation report\nBackground mentions password spraying {report_citation}. Incident cause remains unknown.",
    ]
    for index, node in enumerate(NODES):
        async def invoke(_model, messages, *, i=index):
            prompts.append((i, messages[1].content))
            return SimpleNamespace(content=contents[i], response_metadata={})
        monkeypatch.setattr(node, "safe_ainvoke", invoke)
        monkeypatch.setattr(node, "make_chat_model", lambda *args, **kwargs: object())
        monkeypatch.setattr(node, "record_llm_call", lambda *args, **kwargs: None)
    return prompts


async def four_nodes(value):
    for node in (recon_agent.run_recon, forensic_agent.run_forensic, responder_agent.run_responder, report_writer_agent.run_report_writer):
        value = await node(value)
    return value


@pytest.mark.asyncio
async def test_same_run_reads_once_and_all_actual_model_messages_contain_source_text(monkeypatch, tmp_path):
    row = source()
    calls = api(monkeypatch, tmp_path, rows=[row])
    prompts = models(monkeypatch)
    result = await four_nodes(state().to_dict())
    assert len(calls) == 1 and len(prompts) == 4
    read = result["knowledge_base_read"]
    assert read["status"] == "success" and read["adopted_count"] == 1
    assert all(row["content"] in prompt and "[KB1]" in prompt for _, prompt in prompts)
    assert hashlib.sha256(read["prompt_block"].encode()).hexdigest() == read["prompt_sha256"]
    assert all(read["prompt_block"] in prompt for _, prompt in prompts)
    assert result["run_id"] == RUN and read["model_citations"] == ["KB1"]
    assert len(read["model_citations_by_agent"]) == 4
    assert row["source_url"] in result["report_md"] and row["doc_id"] in result["report_md"]
    assert "chunk 1/1" in result["report_md"] and "content SHA-256" in result["report_md"]
    reads = [entry for entry in result["audit_log"] if entry["metadata"].get("tool") == "knowledge_base.fetch_runbooks"]
    assert len(reads) == 1 and reads[0]["metadata"]["result"]["citations"][0]["doc_id"] == row["doc_id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("status, expected", [(200, "no_match"), (503, "unavailable")])
async def test_missing_source_and_legal_no_match_remain_distinct_in_actual_prompts(monkeypatch, tmp_path, status, expected):
    calls = api(monkeypatch, tmp_path, status=status)
    prompts = models(monkeypatch, report_citation="")
    result = await four_nodes(state().to_dict())
    assert len(calls) == 1 and result["knowledge_base_read"]["status"] == expected
    assert all("status=" + expected in prompt for _, prompt in prompts)
    assert "## Knowledge references" not in result["report_md"]


@pytest.mark.asyncio
@pytest.mark.parametrize("marker", ["", "[KB99]"])
async def test_report_does_not_invent_a_resolved_citation(monkeypatch, tmp_path, marker):
    api(monkeypatch, tmp_path, rows=[source()])
    models(monkeypatch, report_citation=marker)
    result = await four_nodes(state().to_dict())
    facts = result["knowledge_base_read"]["model_citations_by_agent"]["ReportWriterAgent"]
    assert facts["cited_sources"] == []
    assert source()["source_url"] not in result["report_md"]
    assert facts["unresolvable_citations"] == (["KB99"] if marker else [])


@pytest.mark.asyncio
async def test_state_roundtrip_does_not_repeat_source_lookup(monkeypatch, tmp_path):
    calls = api(monkeypatch, tmp_path, rows=[source()])
    original = state()
    await prefetch_knowledge(original)
    restored = InvestigatorState.from_dict(original.to_dict())
    await prefetch_knowledge(restored)
    assert len(calls) == 1 and restored.knowledge_base_read == original.knowledge_base_read


@pytest.mark.asyncio
async def test_reference_metadata_is_literal_report_text(monkeypatch, tmp_path):
    row = source()
    row["title"] = '<img src=x onerror=alert(1)> [link](javascript:alert(1))'
    api(monkeypatch, tmp_path, rows=[row])
    value = state()
    await prefetch_knowledge(value)
    record_knowledge_citations(value, "ReportWriterAgent", "Background [KB1].")
    references = report_knowledge_references(value)
    rendered = report_writer_agent._md_to_html(references, CASE)
    assert "<img" not in rendered and 'href="javascript:' not in rendered
