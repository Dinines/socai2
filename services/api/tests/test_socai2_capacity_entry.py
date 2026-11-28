"""Generated snapshots only: candidate builders, private output and tokenizer boundary."""
import copy
import hashlib
import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import test_socai2_case_material_mirrors as generated
from app.socai2 import baseline_enrichment, case_followup_input, runtime_policy
from app.socai2.baseline_context import PROJECTION, SCHEMA, reference
from app.socai2.baseline_store import digest, encoded

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("capacity_entry", ROOT / "docs/operations/measure_case_input_capacity.py")
entry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entry)


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    policy_path = ROOT / "deploy/local-investigation/investigation-policy-case-v1.toml"
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(policy_path))
    runtime_policy.active_policy.cache_clear()
    policy = runtime_policy.active_policy()
    aid, material = generated.material()
    raw = generated.context(policy.case_io, aid, material).model_dump(mode="json")
    raw["case_input_profile"] = {"version": uuid4().hex, "sha256": uuid4().hex, "business_sha256": uuid4().hex}
    raw["questions"] = [{"id": key, "text": uuid4().hex, "scope": copy.deepcopy(raw["scope"]),
        "evidence_requirements": [], "state": "open", "answer": None, "evidence_refs": [], "limitations": []}
        for key in ("coverage", "behavior")]
    run_id, tenant = str(uuid4()), str(uuid4())
    now = datetime.now(UTC)
    steps = [{"id": str(uuid4()), "run_id": run_id, "tenant_id": tenant, "kind": "stage", "seq": seq,
        "stage_code": code, "state": state, "started_at": (now + timedelta(seconds=seq)).isoformat()}
        for seq, code, state in ((1, "C2", "completed"), (2, "C3", "failed"),
                                 (3, "C4.routing", "completed"), (4, "C6", "skipped"), (5, "C6", "completed"))]
    artifacts = []
    def artifact(body, *, step=None, kind="source_snapshot", schema=None, captured=None):
        row = {"id": str(uuid4()), "tenant_id": tenant, "run_id": run_id, "case_id": raw["case_id"],
            "kind": kind, "schema_version": schema or body.get("schema_version", uuid4().hex),
            "step_id": step["id"] if step else None, "captured_at": captured or (step["started_at"] if step else now.isoformat()),
            "content_json": body, "sha256": digest(body)}
        artifacts.append(row)
        return row["id"]
    context_id = artifact(raw, schema=SCHEMA)
    manifest_id = artifact({"projection_version": PROJECTION,
        "source_materials": [reference("artifact", context_id, "execution_receipt")]}, kind="input_snapshot")
    background_id = artifact({"schema_version": baseline_enrichment.SCHEMA, "sources": []}, step=steps[0])
    artifact({"type": "materials", "members": {aid: {"state": "available", "material_state": "complete",
        "material_id": material["id"], "limitations": [], "omissions": []}}, "catalog": {"bindings": {}}}, step=steps[0])
    bindings_id = artifact({"type": "capacity_preflight", "stage": "C3", "dispatch_state": "not_sent",
        "binding_map": {}, "body": {"model": policy.model.alias, "max_tokens": policy.model.output_tokens["C3"]}}, step=steps[1])
    prior_id = artifact({"analysis": None, "state": "failed", "validation": "not_accepted", "source_map": {}}, step=steps[1])
    steps[1]["output_artifact_id"] = prior_id
    dispatch_id = artifact({"type": "followup_dispatch", "initial_analysis_artifact_id": prior_id, "routes": []}, step=steps[2])
    report_id = artifact({"type": "delivery_report", "comparison": {"state": "initial", "result_id": None}}, step=steps[3])
    markdown = "# " + uuid4().hex
    markdown_id = str(uuid4())
    artifacts.append({**artifacts[-1], "id": markdown_id, "kind": "report_markdown", "content_json": None,
        "content_text": markdown, "blob_ref": None, "mime_type": "text/markdown", "material_state": "complete",
        "sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(), "size_bytes": len(markdown.encode("utf-8"))})
    later_id = artifact({"type": "later_record", "text": uuid4().hex}, step=steps[4])
    run = {"id": run_id, "tenant_id": tenant, "case_id": raw["case_id"], "started_at": now.isoformat(),
        "input_artifact_id": manifest_id, "limits": {"policy_version": policy.identity}}
    snapshot = tmp_path / "generated-snapshot.json"
    snapshot.write_bytes(encoded({"runs": [run], "run_steps": steps, "artifacts": artifacts, "alert_materials": [material]}))
    config = {"mode": "candidate_rebuild_tokenizer_only", "snapshot": {"path": str(snapshot),
        "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest()}, "run_id": run_id,
        "artifacts": {"context": context_id, "enrichment_summary": background_id, "c3_bindings": bindings_id,
            "c3_result": prior_id, "c4_dispatch": dispatch_id, "c6_report": report_id},
        "policy": {"path": str(policy_path), "sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest()},
        "candidate_case_profile": policy.case_io.identity, "tokenizer": {"endpoint": "http://127.0.0.1:1/tokenize"},
        "output_dir": str(tmp_path), "stages": ["C3", "C6"]}
    config_path = tmp_path / "config.json"
    config_path.write_bytes(encoded(config))
    yield config, config_path, policy, {context_id, manifest_id}, {report_id, later_id, markdown_id}
    runtime_policy.active_policy.cache_clear()


def test_generated_candidate_builds_private_reports_without_generation(fixture, monkeypatch, capsys):
    config, config_path, policy, initial_ids, excluded_ids = fixture
    calls, followup = [], []
    original_build = case_followup_input.build
    def observed_build(stage, context, base, artifacts, **kwargs):
        assert initial_ids <= set(artifacts)
        assert not excluded_ids.intersection(artifacts)
        assert kwargs["previous"] is None and kwargs["prior_id"] is None
        assert kwargs["extra"]["preliminary_analysis"] == {"state": "unavailable", "reason": "no_accepted_main_analysis"}
        followup.append(stage)
        return original_build(stage, context, base, artifacts, **kwargs)
    monkeypatch.setattr(case_followup_input, "build", observed_build)
    def tokenizer(request):
        calls.append(request)
        assert request.method == "POST" and request.url.path == "/tokenize"
        assert "max_tokens" not in json.loads(request.content)
        return httpx.Response(200, json={"count": 1, "max_model_len": policy.model.context_tokens})
    def transport(endpoint, output):
        return entry.tokenizer_transport(endpoint, output, inner=httpx.MockTransport(tokenizer))
    original_measure = entry.measure_batch
    async def measured(value):
        return await original_measure(value, transport_factory=transport)
    monkeypatch.setattr(entry, "measure_batch", measured)
    monkeypatch.setattr(sys, "argv", ["measure_case_input_capacity.py", "--config", str(config_path)])
    before = Path(config["snapshot"]["path"]).read_bytes()
    assert entry.main() == 0
    shown = capsys.readouterr()
    assert json.loads(shown.out) == {"status": "local_report_saved", "report_directory": config["output_dir"]}
    assert shown.err == ""
    report = json.loads((config_path.parent / "candidate-redacted-report.json").read_bytes())
    assert all(set(row) == {"stage", "measurement_state", "input_tokens", "available_input_tokens", "fits"} for row in report)
    assert all(row["measurement_state"] == "measured" for row in report)
    assert len(calls) == 4 and followup == ["C6"]
    assert Path(config["snapshot"]["path"]).read_bytes() == before
    identity = json.loads((config_path.parent / "candidate-context-identity.json").read_bytes())
    assert identity["original_profile"] != identity["candidate_profile"] == policy.case_io.identity
    for stage in config["stages"]:
        body = json.loads((config_path.parent / stage / "request.json").read_bytes())
        assert set(body) == {"model", "messages", "max_tokens", "temperature", "response_format"}
        assert body["max_tokens"] == policy.model.output_tokens[stage]
    assert entry.candidate_row("C6") == {"stage": "C6", "measurement_state": "unavailable", "input_tokens": None,
                                         "available_input_tokens": None, "fits": None}


@pytest.mark.parametrize("content_state", ["missing", "corrupt"])
def test_selected_json_source_still_requires_content_and_hash(fixture, content_state):
    config, _, _, _, _ = fixture
    snapshot = Path(config["snapshot"]["path"])
    data = json.loads(snapshot.read_bytes())
    context_id = config["artifacts"]["context"]
    context = next(row for row in data["artifacts"] if row["id"] == context_id)
    context["content_json"] = None if content_state == "missing" else {"schema_version": uuid4().hex}
    snapshot.write_bytes(encoded(data))
    config["snapshot"]["sha256"] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    frozen = entry.Frozen(config)
    with pytest.raises(entry.Unavailable, match="frozen_artifact_invalid"):
        frozen.selected("context")


def test_transport_rejects_generation_and_repeat_attempts(tmp_path):
    async def check():
        endpoint = "http://127.0.0.1:1/tokenize"
        called = []
        def response(request):
            called.append(request)
            return httpx.Response(200, json={"count": 1})
        transport = entry.tokenizer_transport(endpoint, tmp_path, inner=httpx.MockTransport(response))
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(entry.Unavailable, match="non_tokenizer_request_rejected"):
                await client.post("http://127.0.0.1:1/chat/completions", json={})
            with pytest.raises(entry.Unavailable, match="non_tokenizer_payload_rejected"):
                await client.post(endpoint, json={"messages": [], "max_tokens": 1})
            value = {"model": uuid4().hex, "add_special_tokens": False, "return_token_strs": False, "prompt": uuid4().hex}
            await client.post(endpoint, json=value)
            await client.post(endpoint, json=value)
            with pytest.raises(entry.Unavailable, match="tokenizer_retry_rejected"):
                await client.post(endpoint, json=value)
        assert len(called) == 2
        with pytest.raises(entry.Unavailable):
            entry.tokenizer_endpoint("https://example.com/tokenize")
    import asyncio
    asyncio.run(check())
