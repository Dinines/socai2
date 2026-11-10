"""C6 projection minimum, original roles/refs, and post-trim visibility."""
import asyncio
import copy
import json

import pytest
from app.socai2.baseline_final_evidence import query_candidates, share_query_context
from app.socai2.baseline_reanalysis import BaselineReanalysis
from app.socai2.baseline_reasoning import bounded_input, fit_final_request
from app.socai2.baseline_store import StoreError, digest, encoded
from app.socai2.model_input_view import items, queries
from rebuild_socai2_followup_wire_20261105 import DIRECTORY, rebuild


def packet(tool="network_connections", names=("dest_ip", "dst_port"), *, role="observation"):
    values = {"dest_ip": "198.51.100.30", "dst_port": 443,
        "process_command_line": "python inspect.py", "source_ip": "192.0.2.1"}
    fields = [{"name": name, "value": values.get(name, "reported"), "source_path": f"$.original.{i}",
        "transform": "identity", "conflict": name == "dest_ip"} for i, name in enumerate(names)]
    value = {"type": "query_projection", "rows": [{"semantics": {"fields": fields}}] if fields else [],
        "alert_ids": ["A"], "source_role": role}
    identity = "00000000-0000-0000-0000-000000000001"
    query = {"artifact_id": identity, "tool_name": tool, "observed_rows_in_bounded_fetch": int(bool(fields)),
        "state": "completed", "hostname": "host", "window_start": None, "window_end": None}
    return [query], [{"id": identity, "content_json": value, "sha256": digest(value)}]


def identify(candidates):
    for i, candidate in enumerate(candidates, 1):
        candidate["entry"]["id"] = f"S{i}"
    return candidates


def test_common_context_expands_losslessly_without_missing_null_or_type_conflation():
    original = [{"artifact_id": "1", "tool_name": "process_activity", "hostname": "host1", "reason": None,
        "limits": ["exact"], "window_start": "start", "state": "completed", "typed": True},
        {"artifact_id": "2", "tool_name": "network_connections", "hostname": "host2",
        "limits": ["exact"], "window_start": "start", "state": "completed", "typed": 1}]
    data = {"queries": copy.deepcopy(original)}
    share_query_context(data)
    assert queries(data) == original
    assert set(data["query_context"]) == {"applies_to", "limits", "window_start", "state"}
    assert "reason" in data["queries"][0] and "reason" not in data["queries"][1]


def test_network_minimum_keeps_endpoint_same_row_and_conflicting_alternative_as_candidate():
    qs, bases = packet(names=("source_ip", "dest_ip", "dst_port", "dest_ip"))
    fields = bases[0]["content_json"]["rows"][0]["semantics"]["fields"]
    fields[-1]["value"] = "::ffff:198.51.100.30"
    bases[0]["sha256"] = digest(bases[0]["content_json"])
    candidates, missing = query_candidates(qs, bases)
    assert not missing and len(candidates) == 4
    assert [c["entry"]["value"]["name"] for c in candidates if c.get("required")] == ["dest_ip", "dst_port"]
    assert candidates[-1]["entry"]["value"]["conflict"] is True
    assert all(c["source"]["membership_basis"] == "query_binding_only" for c in candidates)
    assert candidates[1]["source"]["ref"]["source_path"] == "$.rows.0.semantics.fields.1"
    assert candidates[1]["entry"]["value"] == {"record_key": "Q1R0", **fields[1]}


@pytest.mark.parametrize(("tool", "names"), [
    ("process_activity", ("event_kind", "src_hostname", "actor_process_command_line")),
    ("network_connections", ("event_kind", "source_ip", "src_hostname")),
])
def test_metadata_or_other_actor_is_not_minimum_query_evidence(tool, names):
    qs, bases = packet(tool, names)
    _, missing = query_candidates(qs, bases)
    assert missing[0]["reason"] == "required_query_evidence_unavailable"


def test_product_source_label_and_empty_query_are_preserved():
    qs, bases = packet("product_host_details", ("product_platform",), role="source_label")
    candidates, missing = query_candidates(qs, bases)
    assert not missing and candidates[0]["required"]
    assert candidates[0]["source"]["ref"]["role"] == candidates[0]["entry"]["role"] == "source_label"
    qs, bases = packet(names=())
    assert query_candidates(qs, bases) == ([], [])
    qs[0]["observed_rows_in_bounded_fetch"] = 1
    assert query_candidates(qs, bases)[1][0]["reason"] == "required_query_evidence_unavailable"


def test_projection_digest_must_match():
    qs, bases = packet()
    bases[0]["content_json"]["rows"][0]["semantics"]["fields"][0]["value"] = "changed"
    with pytest.raises(StoreError, match="evidence_receipt_invalid"):
        query_candidates(qs, bases)


def test_required_query_field_guard_blocks_instead_of_using_metadata(monkeypatch):
    monkeypatch.setattr("app.socai2.baseline_reasoning.field_limit", lambda: 2048)
    qs, bases = packet("process_activity", ("process_command_line",))
    field = bases[0]["content_json"]["rows"][0]["semantics"]["fields"][0]
    field["value"] = "x" * 3000
    bases[0]["sha256"] = digest(bases[0]["content_json"])
    candidates, _ = query_candidates(qs, bases)
    prepared = bounded_input({"queries": qs}, identify(candidates), "test")
    assert not prepared["ready"] and prepared["reason"] == "required_model_input_unavailable"
    assert prepared["omissions"][0]["reason"] == "whole_field_exceeds_budget"


def test_final_wire_trim_keeps_minimum_and_updates_visible_count_and_omission():
    qs, bases = packet(names=("dest_ip", "dst_port", "source_ip"))
    candidates, _ = query_candidates(qs, bases)
    prepared = bounded_input({"queries": qs}, identify(candidates), "test")
    assert prepared["ready"]
    data = json.loads(prepared["messages"][1]["content"])
    assert queries(data)[0]["visible_fields"] == 3
    body = {"messages": prepared["messages"], "response_format": {"json_schema": {
        "schema": {"$defs": {"SourceId": {"enum": sorted(prepared["source_map"])}}}}}}
    fit_final_request(body, prepared, len(encoded(body)) - 1)
    data = json.loads(body["messages"][1]["content"])
    assert {i["value"]["name"] for i in items(data)} == {"dest_ip", "dst_port"}
    assert queries(data)[0]["visible_fields"] == 2
    assert queries(data)[0]["projected_fields"] == 3 and queries(data)[0]["view_state"] == "partial"
    assert prepared["omissions"][-1]["reason"] == "remaining_final_token_budget"
    assert all(s["required"] and s["membership_basis"] == "query_binding_only" for s in prepared["source_map"].values())
    fit_final_request(body, prepared, 1)
    assert len(prepared["source_map"]) == 2  # admission must reject; no required field is dropped


def test_c3_reanalysis_keeps_legacy_query_view_without_c6_minimum(monkeypatch):
    original, captured = BaselineReanalysis.input, {}

    class Captured(Exception):
        pass

    async def intercept(self, *args, **kwargs):
        kwargs["extra_data"] = {"round": "post_evidence_reanalysis"}
        prepared = await original(self, *args, **kwargs)
        captured.update(prepared)
        raise Captured

    monkeypatch.setattr(BaselineReanalysis, "input", intercept)
    with pytest.raises(Captured):
        asyncio.run(rebuild())
    assert captured["ready"]
    data = json.loads(captured["messages"][1]["content"])
    assert "query_context" not in data
    fixture = json.loads((DIRECTORY / "pg-wire-frozen-synthetic.json").read_text())
    view = [a["content_json"] for a in fixture["artifacts"] if (a.get("content_json") or {}).get("type") == "model_view"][-1]
    assert data["queries"] == json.loads(view["messages"][1]["content"])["queries"]
    assert not any(s["required"] for s in captured["source_map"].values()
        if s.get("membership_basis") == "query_binding_only")
