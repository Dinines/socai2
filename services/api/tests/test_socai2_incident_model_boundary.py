"""Frozen originals and altered copies; no model/network/database mutation."""
import copy
import json
from pathlib import Path
from uuid import UUID

import pytest
from app.socai2 import incident_model_boundary as boundary
from app.socai2 import incident_output_adapter as output
from app.socai2 import runtime_policy
from app.socai2.baseline_store import StoreError, digest, encoded
from app.socai2.incident_query_receipts import receipts, reference_roles
from app.socai2.runtime_policy import load_incident_profile as load_profile
from app.socai2.stage_inputs import QUERY_RECEIPTS_VERSION, freshness_sql
from app.socai2.stage_results import validate_refs
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / "docs/operations/evidence/production-multialert-20261108-01/exports/20261108T013952440775Z/database.json"
POLICY = ROOT / "deploy/local-investigation/investigation-policy-incident-v1.toml"


def frozen_sample():
    database = json.loads(SNAPSHOT.read_text())
    run = next(r for r in database["runs"] if r["id"] == "27db8785-fa50-5e08-afef-40150a1310bc")
    source = next(a["content_json"] for a in database["artifacts"] if a["id"] == run["input_artifact_id"])
    source.update(query_receipts_version=QUERY_RECEIPTS_VERSION, triage_queries={})
    for member in source["members"]:
        aid, arid = member["alert"]["id"], member["triage"]["source_run_id"]
        source["triage_queries"][aid] = [a for a in database["artifacts"]
            if a["kind"] == "tool_response" and a["run_id"] == arid and a["alert_id"] == aid
            and any(s["output_artifact_id"] == a["id"] and s["id"] == a["step_id"] and s["run_id"] == arid
                    for s in database["run_steps"])]
    return source, run["input_artifact_id"]


@pytest.fixture
def sample(monkeypatch):
    policy = runtime_policy.load_policy(POLICY)
    monkeypatch.setattr(runtime_policy, "active_policy", lambda: policy)
    return frozen_sample()


def build(sample):
    source, identity = sample
    return boundary.build(source, identity, load_profile({"profile": "incident-input-v1.json"}))[-1]


def answer(prepared):
    selected = {aid: next(sid for sid, s in prepared["source_map"].items()
                          if s["alert_ids"] == [aid] and s["ref"]["role"] == "observation")
                for aid in prepared["member_aliases"]}
    return {"diagnosis": {"summary": "合成结构检查。", "conclusion": "授权情况仍待核实。",
            "source_ids": list(selected.values()), "limitations": []},
        "members": [{"alert_ref": alias, "state": "unresolved", "assessment": "成员记录已阅读，仍需核实。",
                     "source_ids": [selected[aid]], "limitations": []} for aid, alias in prepared["member_aliases"].items()],
        "findings": [], "open_questions": []}


def test_full_frozen_values_and_receipts_are_preserved_without_mutation(sample):
    original = copy.deepcopy(sample)
    prepared = build(sample)
    assert sample == original
    source = sample[0]
    for m in source["members"]:
        assert m["triage"]["rationale"] in prepared["user"]
    assert len(receipts(source)) == 9
    facts = prepared["data"]["program_facts"]["query_statuses"]
    skipped = [q for q in facts if q["state"] == "skipped"]
    assert len(skipped) == 1 and skipped[0]["outcome"] == "not_queried" and skipped[0]["returned_rows"] is None
    assert "本次未执行查询" in prepared["user"] and "no_supported_frozen_objects" in prepared["user"]
    for row in prepared["records"]:
        if row["header"][1] == "execution_receipt" and row["value"]["state"] == "skipped":
            assert "保留行数：0" not in row["rendered_text"]
    assert all(aid not in prepared["user"] for aid in prepared["member_aliases"])
    assert all(item["id"] in prepared["source_map"] for item in prepared["data"]["items"])


def test_nonempty_description_raw_text_and_unknown_business_fields_survive(sample):
    source = sample[0]
    m = source["members"][0]
    m["alert"]["description"] = "采集端说明：有明确原文。\n第二行。"
    m["material"]["raw_text"] = "原始日志原文，不做总结。"
    m["material"]["ocsf_json"].update(cloud={"permissions_after": [], "mfa_enabled": False,
        "vendor.account.id": "业务账号标识"}, email={"id": "业务邮件编号", "size": 0},
        vendor={"connector_type": "业务来源", "confidence_value": 0})
    prepared = build(sample)
    for value in (m["alert"]["description"], m["material"]["raw_text"], "业务账号标识", "业务邮件编号", "业务来源"):
        assert value in prepared["user"]
    values = {item["field"]: item["value"] for item in prepared["data"]["items"]}
    assert values["$.ocsf_json.email.size"] == 0
    assert values["$.ocsf_json.cloud"]["mfa_enabled"] is False
    assert values["$.ocsf_json.cloud"]["permissions_after"] == []
    refs = [s["ref"] for s in prepared["source_map"].values()]
    validate_refs({"source_refs": refs}, source, sample[1], reference_roles(source))


def test_unknown_empty_values_are_retained_and_envelope_rules_are_scoped(sample):
    m = sample[0]["members"][0]
    m["material"]["raw_json"] = {"id": "vendor-business-id", "vendor": {"schema_version": 0}, "empty_result": []}
    prepared = build(sample)
    assert "vendor-business-id" in prepared["user"] and "empty_result：[]" in prepared["user"]
    assert "vendor.schema_version：0" in prepared["user"]


def test_stale_triage_and_its_receipts_cannot_be_used_as_current(sample):
    source = sample[0]
    aid = source["members"][0]["alert"]["id"]
    source["triage_validation"][aid].update(usable=False, freshness="stale")
    with pytest.raises(StoreError, match="incident_query_pairing_invalid"):
        build(sample)
    del source["triage_queries"][aid]
    prepared = build(sample)
    assert not any(s["ref"]["source_path"] == "$.members.0.triage" for s in prepared["source_map"].values())
    member = prepared["data"]["members"][0]
    assert not member["triage_eligible"] and member["triage_visibility"] == "unavailable"
    assert "未提供可核对的本轮告警分诊查询回执" in prepared["user"]


@pytest.mark.parametrize("bad", ["tenant_id", "alert_id", "run_id", "sha256", "size_bytes", "scope", "count"])
def test_bad_receipt_pairing_integrity_or_scope_fails_before_model(sample, bad):
    row = next(iter(sample[0]["triage_queries"].values()))[0]
    if bad == "scope":
        row["content_json"]["actual_args"]["scope"]["alert_ids"] = [str(UUID(int=987))]
    elif bad == "count":
        row["content_json"]["returned_rows"] = 999
    else:
        row[bad] = 1 if bad == "size_bytes" else str(UUID(int=987))
    if bad in {"scope", "count"}:
        row.update(sha256=digest(row["content_json"]), size_bytes=len(encoded(row["content_json"])))
    with pytest.raises(StoreError):
        build(sample)


def test_query_rows_keep_roles_and_exact_original_reference_paths(sample):
    prepared = build(sample)
    roles = reference_roles(sample[0])
    for s in prepared["source_map"].values():
        ref = s["ref"]
        if ref["id"] in roles:
            assert roles[ref["id"]][ref["source_path"]] == ref["role"]
            assert ref["role"] != "observation"
    history = [r for r in prepared["records"] if any(p and p.endswith(".record.triage") for p in r["source_paths"])]
    assert history and all(r["header"][1] == "prior_analysis" for r in history)


def test_output_restores_original_ids_fields_and_exact_sources(sample):
    prepared = build(sample)
    body = answer(prepared)
    Draft202012Validator(output.candidate_schema(prepared)).validate(body)
    result, members = output.parse(json.dumps(body), prepared)
    assert {m["alert_id"] for m in members} == set(prepared["member_aliases"])
    assert {f.id for f in result.findings} == {"member:" + aid for aid in prepared["member_aliases"]}
    payload = result.model_dump(mode="json")
    assert set(payload) == {"summary", "conclusion", "findings", "source_refs", "open_questions", "limitations"}
    validate_refs(payload, sample[0], sample[1], reference_roles(sample[0]))


def test_invalid_citation_retains_independent_member_without_rewriting_raw(sample):
    prepared = build(sample)
    body = answer(prepared)
    body["members"][1]["source_ids"] = body["members"][0]["source_ids"]
    raw = json.dumps(body)
    with pytest.raises(StoreError):
        output.parse(raw, prepared)
    review = output.review(raw, prepared)
    assert len(review["retained_analysis"]["members"]) == 2
    assert review["retained_analysis"]["conclusion"] is None and not review["conclusion_adoptable"]
    assert raw == json.dumps(body)
    assert output.review(raw[:-1] + ',"members":[]}', prepared) is None


def test_policy_selection_and_old_freshness_contract_are_explicit():
    assert runtime_policy.load_policy(ROOT / "deploy/local-investigation/investigation-policy.toml").incident_io is None
    policy = runtime_policy.load_policy(POLICY)
    assert policy.incident_io.sha256 and policy.incident_io.version == "socai2.incident-boundary.v1"
    sql = freshness_sql("incident_diagnosis", "i.id", "d.source_run_id")
    assert "query_receipts_version" in sql and "triage_validation_version" in sql and "ELSE (SELECT jsonb_build_object" in sql
    with pytest.raises(ValueError):
        load_profile({"profile": "../incident-input-v1.json"})


def test_oversize_required_input_is_not_silently_shortened(sample, monkeypatch):
    monkeypatch.setattr(boundary, "draft_limit", lambda: 1000)
    with pytest.raises(StoreError, match="incident_required_input_view_size"):
        build(sample)
