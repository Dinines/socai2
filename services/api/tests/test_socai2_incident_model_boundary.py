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
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(POLICY))
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
    assert "威胁情报：未查询" in prepared["user"]
    assert "no_supported_frozen_objects" not in prepared["user"]
    for row in prepared["records"]:
        if row["header"][1] == "execution_receipt" and row["value"]["state"] == "skipped":
            assert row["rendered_text"] == "威胁情报：未查询"
            assert row["value"]["reason"] == "no_supported_frozen_objects"
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
    assert "查询结果：未知" in prepared["user"]


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


def test_repeated_history_matches_share_text_but_keep_each_reference(sample):
    row = next(row for _, row in receipts(sample[0]) if row["content_json"]["tool_name"] == "history"
               and row["content_json"].get("rows"))
    body = row["content_json"]
    original = copy.deepcopy(body["rows"][0])
    original["record"]["observed_count"] = 0
    duplicate, changed, other = [copy.deepcopy(original) for _ in range(3)]
    duplicate["object_key"] = "same-record-matched-by-another-object"
    changed["record"]["title"] += " changed"
    other["record_id"] = other["record"]["id"] = str(UUID(int=999))
    body.update(rows=[original, duplicate, changed, other], returned_rows=4)
    row.update(sha256=digest(body), size_bytes=len(encoded(body)))
    before = copy.deepcopy(sample)
    prepared = build(sample)
    sources = {sid: source for sid, source in prepared["source_map"].items()
               if source["ref"]["id"] == row["id"] and (source["ref"]["source_path"] or "").count(".") == 2}
    assert len(sources) == 4
    groups = [record for record in prepared["records"] if any(sid in sources for sid in record["source_ids"])]
    assert sorted(len(record["source_ids"]) for record in groups) == [1, 1, 2]
    shared = next(record for record in groups if len(record["source_ids"]) == 2)
    assert shared["source_paths"] == ["$.rows.0", "$.rows.1"]
    assert sample == before and body["returned_rows"] == 4


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


def test_history_selection_keeps_required_rows_and_shares_text_without_broadening_sources(sample):
    histories = [(aid, row) for aid, row in receipts(sample[0]) if row["content_json"]["tool_name"] == "history"]
    (aid, first), (other_aid, second) = histories[:2]
    def row(number, title):
        rid = str(UUID(int=number))
        return {"record_id": rid, "object_key": "backend-match-only", "namespace": "backend-namespace-only",
                "match_basis": "exact_typed_namespaced_object", "record": {"id": rid, "title": title}}
    discarded, required, rich = row(801, "纯目录不上送"), row(802, "A明确引用的目录"), row(803, "相关历史业务")
    rich["record"].update(observed_count=0, authorized=False, permissions_after=[],
        triage={"id": str(UUID(int=804)), "verdict": "false_positive", "rationale": "历史机器判断原文。"},
        feedback={"id": str(UUID(int=805)), "verdict": "true_positive", "rationale": "人工提供相反事实的原文。"})
    duplicate, changed = copy.deepcopy(rich), copy.deepcopy(rich)
    duplicate["object_key"] = "another-backend-match"
    changed["record"]["triage"]["rationale"] = "另一版本的历史判断原文。"
    first["content_json"].update(rows=[discarded, required, rich, duplicate, changed], returned_rows=5)
    second["content_json"].update(rows=[copy.deepcopy(rich)], returned_rows=1)
    for receipt in (first, second):
        receipt.update(sha256=digest(receipt["content_json"]), size_bytes=len(encoded(receipt["content_json"])))
    member = next(m for m in sample[0]["members"] if m["alert"]["id"] == aid)
    member["triage"]["source_refs"] = [{"type": "artifact", "id": first["id"], "role": "source_label",
                                        "source_path": "$.rows.1"}]
    original = copy.deepcopy(sample)
    prepared = build(sample)
    assert sample == original
    assert "纯目录不上送" not in prepared["user"] and "A明确引用的目录" in prepared["user"]
    for value in ("历史机器判断原文。", "人工提供相反事实的原文。", "另一版本的历史判断原文。",
                  '"observed_count":0', '"authorized":false', '"permissions_after":[]'):
        # Records may use the text template instead of JSON punctuation.
        assert value in prepared["user"] or value in json.dumps([r["value"] for r in prepared["records"]], ensure_ascii=False, separators=(",", ":"))
    assert "backend-match-only" not in prepared["user"] and "source_refs" not in prepared["user"]
    shared = next(r for r in prepared["records"] if r["history"] and r["value"].get("rationale") == "历史机器判断原文。")
    assert len(shared["header"][0]) == 2 and len(shared["source_ids"]) == 3
    for sid in shared["source_ids"]:
        source = prepared["source_map"][sid]
        assert source["alert_ids"] == ([aid] if source["ref"]["id"] == first["id"] else [other_aid])
    refs = [s["ref"] for s in prepared["source_map"].values()]
    validate_refs({"source_refs": refs}, sample[0], sample[1], reference_roles(sample[0]))
    # Shared display must not make one member's receipt usable for another.
    body = answer(prepared)
    target = next(m for m in body["members"] if m["alert_ref"] == prepared["member_aliases"][other_aid])
    target["source_ids"] = [next(s for s in shared["source_ids"] if prepared["source_map"][s]["alert_ids"] == [aid])]
    with pytest.raises(StoreError):
        output.parse(json.dumps(body), prepared)


def test_serialized_material_keeps_unique_values_in_its_own_member(sample):
    material = sample[0]["members"][0]["material"]
    material["ocsf_json"]["business_size"] = 0
    sample[0]["members"][1]["material"]["ocsf_json"]["additional_allowed"] = False
    material["raw_text"] = '{"business_size":0,"additional_allowed":false,"additional_permissions":[]}'
    original = copy.deepcopy(sample)
    prepared = build(sample)
    selected = next(r for r in prepared["records"] if "$.raw_text" in r["source_paths"]
                    and prepared["source_map"][r["source_ids"][0]]["ref"]["id"] == material["id"])
    assert selected["value"] == {"additional_allowed": False, "additional_permissions": []}
    assert "additional_allowed：false" in prepared["user"] and "additional_permissions：[]" in prepared["user"]
    assert material["raw_text"] not in prepared["user"] and sample == original


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
