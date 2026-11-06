"""C3 offers fixed query scopes using the host actually queried by the lake."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

from app.socai2.baseline_contracts import Limits
from app.socai2.baseline_dispatch import offered_bindings, ranked_bindings
from app.socai2.baseline_evidence_tools import TOOLS
from app.socai2.baseline_store import encoded


def field(name, path, value, *, conflict=False):
    return {"name": name, "source_path": "$.ocsf_json." + path, "value": value, "conflict": conflict}


def binding(host, tool, members):
    key = '["host","' + host + '"]'
    return {"hostname": host, "tool_name": tool, "alert_ids": members,
        "objects": [{"object_key": key, "alert_id": aid} for aid in members],
        "scope": {"window_start": "2026-11-06T12:49:00Z", "window_end": "2026-11-06T12:51:00Z"}}


def test_selector_preserves_matching_scopes_before_catalog_byte_limit():
    aids = [str(UUID(int=i)) for i in range(1, 4)]
    kinds = ("process_activity", "process_activity", "authentication_activity")
    members = {aid: {"fields": [field("event_kind", "class_uid", kind),
        field("device_name", "device.name", "source"), field("dst_hostname", "dst_endpoint.hostname", "remote")]}
        for aid, kind in zip(aids, kinds, strict=True)}
    # All decoy IDs sort first and claim the same member coverage. The hash by
    # itself and member count alone cannot identify the query's source host.
    bindings = {f"a{i}": binding(f"remote-{i}", "process_activity", aids) for i in range(9)}
    bindings.update({"zz-" + tool: binding("source", tool, aids) for tool in TOOLS})
    now = datetime.now(UTC)
    limits = Limits(max_model_calls=4, max_tool_calls=4, max_tokens=48000, max_rows_per_query=200,
        deadline_at=now + timedelta(seconds=120), policy_version="test")
    options, mapping, excluded = offered_bindings({"bindings": bindings}, limits, now, [],
        SimpleNamespace(configured=lambda: True), members=members)
    assert [(o["hostname"], o["tool_name"]) for o in options[:3]] == [
        ("source", "process_activity"), ("source", "authentication_activity"), ("source", "network_connections")]
    assert excluded and len(encoded(options)) <= 1800
    assert all(e["reason"] == "binding_catalog_input_limit" for e in excluded)
    assert {e["binding_id"] for e in excluded}.isdisjoint(b["binding_id"] for b in mapping.values())
    for opt in options:
        original = bindings[mapping[opt["binding_id"]]["binding_id"]]
        assert original["alert_ids"] == opt["alert_ids"] and original["hostname"] == opt["hostname"]
        assert {o["object_key"] for o in original["objects"]} == set(opt["object_keys"])


def test_lake_host_precedence_conflicts_and_legacy_materials():
    aid = "member"
    hosts = ("first", "second", "third")
    catalog = {"bindings": {host: binding(host, "process_activity", [aid]) for host in hosts}}

    def first(fields):
        return ranked_bindings(catalog, {aid: {"fields": fields}})[0][0]

    src = field("src_hostname", "src_endpoint.hostname", "second")
    assert first([src, field("device_name", "device.name", "third")]) == "third"
    assert first([src, field("device_name", "device.hostname", "third")]) == "second"
    assert first([field("dst_hostname", "dst_endpoint.hostname", "third")]) == "first"
    assert first([src, field("device_name", "device.name", "third", conflict=True)]) == "first"
    assert first([field("src_hostname", "src_endpoint.hostname", "SECOND")]) == "first"
    assert first([{"name": "device_name", "value": "third"}]) == "first"
    assert first([{k: v for k, v in src.items() if k != "conflict"}]) == "first"
    assert [bid for bid, _ in ranked_bindings(catalog, None)] == list(hosts)
