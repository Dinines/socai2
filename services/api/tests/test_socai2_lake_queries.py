"""Direct 3f read contracts using synthetic rows; native validation is separate."""
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from app.core.config import settings
from app.db.clickhouse_owned import LakeQueryInterrupted, LakeQueryRejected
from app.socai2 import baseline_evidence_tools as tools
from app.socai2 import lake_evidence_v2 as v2
from app.socai2.lake_hostname import hostname_key
from app.socai2.lake_queries import (
    EVIDENCE_FIELDS,
    MAPPING,
    SUMMARY_FIELDS,
    LakeQueries,
    LakeQueryProfile,
    normalize_rows,
    record_ref,
    search_sql,
    validate_search_rows,
)
from app.socai2.lake_query_contracts import LakeReadError, LakeRecordRef, LakeSearch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from investigation_http.adapters.identity import BusinessContext
from investigation_http.adapters.lake import LakeReadBackend
from investigation_http.dependencies import lake_read_service
from investigation_http.external_routes.lake import router
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / "docs/operations/evidence/lake-query-3f-20261119-01/query-synthetic.json"
TENANT = UUID("10000000-0000-0000-0000-000000000001")
TIME = datetime(2026, 11, 19, tzinfo=UTC)


@pytest.fixture
def profile():
    return LakeQueryProfile.load(PROFILE, database="lyc_lake_3f_synthetic_20261119_01")


def query(**changes):
    return LakeSearch(**{"source_namespace": "lyc-lake-query", "mapping_version": MAPPING,
        "selector": {"role": "device", "kind": "hostname", "value": "HOST-A"}, "time_basis": "event",
        "start": TIME, "end": TIME+timedelta(hours=1), "limit": 1, **changes})


def row(identity=1, **changes):
    return {**dict.fromkeys(EVIDENCE_FIELDS, ""), "event_id": str(UUID(int=identity)), "tenant_id": str(TENANT),
        "event_time": TIME.isoformat(), "ingest_time": (TIME+timedelta(minutes=1)).isoformat(),
        "class_uid": 4001, "source_namespace": "lyc-lake-query", "mapping_version": MAPPING,
        "source_version": "version-"+str(identity), "source_event_id": str(identity), "event_time_source": "ocsf_time_ms",
        "parse_status": "parsed", "device_hostname": "Host-A", "device_ip": "::ffff:192.0.2.1",
        "src_hostname": "source-a", "source_ip": "::ffff:192.0.2.2", "dst_hostname": "dest-a", "dest_ip": "2001:db8::3",
        "src_port": 0, "dst_port": 0, "is_alert": None, **changes}


def executor(rows, fields=SUMMARY_FIELDS):
    async def execute(sql, **kwargs):
        assert kwargs["extra_settings"]["readonly"] == 2
        assert kwargs["extra_settings"]["result_overflow_mode"] == "throw"
        return SimpleNamespace(columns=list(fields), rows=[[r[f] for f in fields] for r in rows])
    return execute


def test_scope_role_and_after_dedup_sql(profile):
    sql, params, *_ = search_sql(profile, TENANT, query())
    assert sql.index("source_rank=1") < sql.index("lower(device_hostname)")
    assert "event_time_source='ocsf_time_ms'" in sql
    assert params["value"] == "host-a" and params["tenant_id"] == str(TENANT)
    for changes in ({"source_namespace": "other"}, {"mapping_version": "other"},
                    {"selector": {"role": "legacy_host", "kind": "hostname", "value": "host-a"}},
                    {"time_basis": "legacy_event"}, {"limit": 101}, {"end": TIME}, {"class_uids": []}):
        with pytest.raises(LakeReadError):
            search_sql(profile, TENANT, query(**changes))
    with pytest.raises(LakeReadError):
        search_sql(profile, UUID(int=2), query())


@pytest.mark.parametrize("value", [True, "4001", 4001.5, -1, 2**32])
def test_class_filter_is_strict(value):
    with pytest.raises(ValidationError):
        query(class_uids=[value])


def test_ip_and_legacy_are_explicit(profile):
    sql, bound, *_ = search_sql(profile, TENANT, query(selector={"role": "source", "kind": "ip", "value": "::ffff:192.0.2.2"}))
    assert "source_ip=toIPv6" in sql and bound["value"] == "192.0.2.2"
    legacy = query(source_namespace="", mapping_version="", time_basis="legacy_event",
        selector={"role": "legacy_host", "kind": "hostname", "value": "host-a"})
    sql, *_ = search_sql(profile, TENANT, legacy)
    assert "lower(src_hostname)" in sql and "event_time_source='ocsf_time_ms'" not in sql
    for selector in ({"role": "device", "kind": "ip", "value": "192.0.2.1"},
                     {"role": "source", "kind": "hostname", "value": "host-a"}):
        with pytest.raises(LakeReadError):
            search_sql(profile, TENANT, legacy.model_copy(update={"selector": query(selector=selector).selector}))


@pytest.mark.asyncio
async def test_paging_and_reference(profile):
    result = await LakeQueries(profile, executor([row(1), row(2)])).search(TENANT, query())
    assert len(result.items) == 1 and result.has_more and result.next_cursor
    assert result.items[0].record_ref.source_version == "version-1"
    assert result.items[0].device_ip == "192.0.2.1"
    sql, params, *_ = search_sql(profile, TENANT, query(cursor=result.next_cursor))
    assert "after_id" in sql and params["after_id"] == str(UUID(int=1))
    with pytest.raises(LakeReadError, match="invalid_lake_cursor"):
        search_sql(profile, TENANT, query(cursor=result.next_cursor, time_basis="ingest"))


@pytest.mark.asyncio
async def test_reliable_time_and_row_scope_validation(profile):
    for changes in ({"event_time_source": "unknown"}, {"source_namespace": "other"}, {"tenant_id": str(UUID(int=2))},
                    {"device_hostname": "other"}):
        with pytest.raises(LakeReadError, match="lake_row_outside_bound_scope"):
            await LakeQueries(profile, executor([row(**changes)])).search(TENANT, query())
    result = await LakeQueries(profile, executor([row(event_time_source="unknown")])).search(TENANT, query(time_basis="ingest"))
    assert result.items[0].event_time_source == "unknown"
    with pytest.raises(LakeReadError):
        await LakeQueries(profile, executor([row(), row()])).search(TENANT, query())


@pytest.mark.asyncio
async def test_source_time_browse_without_indexed_object(profile):
    original = row(device_hostname="", src_hostname="", dst_hostname="", device_ip=None,
                   source_ip="::", dest_ip="::", event_time_source="missing")
    q = query(selector=None, time_basis="ingest")
    sql, *_ = search_sql(profile, TENANT, q)
    assert "lower(" not in sql and "source_namespace=" in sql and "ingest_time>=" in sql
    result = await LakeQueries(profile, executor([original])).search(TENANT, q)
    assert len(result.items) == 1 and result.selector is None
    assert result.items[0].device_ip is None and result.items[0].source_ip is None


@pytest.mark.asyncio
async def test_complete_material_and_exact_version(profile):
    original = row(ocsf_json=json.dumps({"message": "正文"*150000}), raw_payload="original"*20000)
    service = LakeQueries(profile, executor([original], (*SUMMARY_FIELDS, "ocsf_json", "raw_payload")))
    ref = LakeRecordRef(**record_ref(original))
    result = await service.material(TENANT, ref)
    assert result.completeness == "complete" and result.ocsf_json == original["ocsf_json"]
    assert result.raw_payload == original["raw_payload"]
    with pytest.raises(LakeReadError, match="lake_material_reference_mismatch"):
        await service.material(TENANT, ref.model_copy(update={"source_version": "another"}))
    with pytest.raises(LakeReadError) as missing:
        await LakeQueries(profile, executor([], (*SUMMARY_FIELDS, "ocsf_json", "raw_payload"))).material(TENANT, ref)
    assert missing.value.status == 404


@pytest.mark.parametrize(("body", "expected"), [("{}", "legacy_unverified"),
    ('{"_socai2_storage":{"truncated":true},"preview":"prefix"}', "preview"),
    ('{"_socai2_storage":{"raw_payload":{"truncated":true}}}', "preview")])
@pytest.mark.asyncio
async def test_legacy_preview_never_claimed_complete(profile, body, expected):
    original = row(mapping_version="", source_namespace="", ocsf_json=body)
    result = await LakeQueries(profile, executor([original], (*SUMMARY_FIELDS, "ocsf_json", "raw_payload"))).material(TENANT, LakeRecordRef(**record_ref(original)))
    assert result.completeness == expected and result.raw_payload_encoding == "legacy_unspecified"


@pytest.mark.asyncio
async def test_empty_failed_unknown_are_distinct(profile):
    result = await LakeQueries(profile, executor([])).search(TENANT, query())
    assert result.state == "completed" and result.items == []
    for error, state, status in ((LakeQueryRejected("rejected"), "failed", 502),
                                 (LakeQueryInterrupted("interrupted", [], []), "unknown", 504)):
        async def execute(*args, failure=error, **kwargs):
            raise failure
        with pytest.raises(LakeReadError) as raised:
            await LakeQueries(profile, execute).search(TENANT, query())
        assert (raised.value.state, raised.value.status) == (state, status)


@pytest.mark.parametrize("hostname", ["Host-A", "终端-A_01.办公"])
def test_http_search_to_material_and_errors(profile, hostname):
    original = row(device_hostname=hostname, class_uid=5001,
        ocsf_json=json.dumps({"class_uid": 5001, "device": {"hostname": hostname}}, ensure_ascii=False), raw_payload="full raw")
    async def execute(sql, **kwargs):
        fields = (*SUMMARY_FIELDS, "ocsf_json", "raw_payload") if "LIMIT 2" in sql else SUMMARY_FIELDS
        return await executor([original], fields)(sql, **kwargs)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.state.business_context = BusinessContext(TENANT, UUID(int=2), "lyc test")
    app.dependency_overrides[lake_read_service] = lambda: LakeReadBackend(LakeQueries(profile, execute))
    with TestClient(app) as client:
        body = query(selector={"role": "device", "kind": "hostname", "value": hostname_key(hostname)}, class_uids=[5001])
        response = client.post("/api/v1/socai2/lake/events/search", json=body.model_dump(mode="json"))
        assert response.status_code == 200, response.text
        item = response.json()["items"][0]
        material = client.get(item["material_url"])
        assert material.status_code == 200 and material.json()["ocsf_json"] == original["ocsf_json"]
        assert material.json()["raw_payload"] == original["raw_payload"]
        assert item["device_hostname"] == hostname and item["source_event_id"] == original["source_event_id"]
        assert client.get(item["material_url"]+"&class_uid=4001").status_code == 422
        assert client.post("/api/v1/socai2/lake/events/search", json=query(source_namespace="other").model_dump(mode="json")).status_code == 422


@pytest.mark.parametrize("hostname", ["HOST-A", "终端-A_01.办公", "Ä-İ-Σ-E\u0301"])
def test_c4_v2_frozen_roles_and_v1_compatibility(profile, monkeypatch, hostname):
    from app.socai2.baseline_contracts import Scope
    from app.socai2.baseline_dispatch import ranked_bindings
    scope = Scope(kind="whole_case", alert_ids=[], object_keys=[], limitations=[], window_start=TIME, window_end=TIME+timedelta(hours=1))
    alert = SimpleNamespace(objects=[{"object_type": "host", "normalized_value": hostname, "id": "obj1",
        "object_key": "host:host-a", "namespace": "test"}], alert={})
    context = SimpleNamespace(alerts={"a": alert}, case_id=UUID(int=3), scope=scope, query_preparation=None)
    catalog = v2.catalog(context, TENANT, profile=profile)
    bindings = [b for b in catalog["bindings"].values() if b["mapping_version"]]
    assert len(bindings) == 9 and {b["selector"]["role"] for b in bindings} == {"device", "source", "destination"}
    assert catalog["omissions"] == []
    assert all(b["selector"]["value"] == hostname_key(hostname) for b in bindings)
    assert all(set(v2.subject(b)) == {"selector"} for b in bindings)
    from app.socai2.baseline_tool_catalog import data
    grouped = data([{"binding_id": "B1", "tool_name": b["tool_name"], **v2.subject(b),
                     "alert_ids": b["alert_ids"], "object_keys": []} for b in bindings])
    assert grouped["schema_version"] == "socai2.c3-tool-catalog.v3"
    assert all("selector" in group for group in grouped["tool_option_groups"])
    assert "source_namespace" not in json.dumps(grouped) and "query_profile_digest" not in json.dumps(grouped)
    assert len(ranked_bindings(catalog, {})) == len(catalog["bindings"])
    monkeypatch.setattr(settings, "SOCAI2_LAKE_QUERY_PROFILE_FILE", str(PROFILE))
    monkeypatch.setattr(settings, "CLICKHOUSE_DATABASE", profile.database)
    assert tools.catalog(context, TENANT) == catalog
    binding = next(b for b in bindings if b["selector"]["role"] == "device" and b["tool_name"] == "network_connections")
    args = {"contract_version": v2.VERSION, "tool_name": binding["tool_name"], "scope": binding["scope"],
        "limit": 1, "row_limit": 1, "parameters": {"tenant_id": str(TENANT), **v2.parameters(binding)}}
    sql, params = tools.query_sql(args)
    assert "lower(device_hostname)=%(value)s" in sql and params["value"] == hostname_key(hostname)
    tools.validate_rows(normalize_rows([row(device_hostname=hostname)]), args)
    args["parameters"]["query_profile_digest"] = "changed"
    with pytest.raises(LakeReadError, match="frozen_lake_query_profile_changed"):
        tools.query_sql(args)
    monkeypatch.setattr(settings, "SOCAI2_LAKE_QUERY_PROFILE_FILE", "")
    old = tools.catalog(context, TENANT)
    assert len(old["bindings"]) == 3 and all(b["contract_version"] == tools.VERSION for b in old["bindings"].values())
    assert old["omissions"] == [] and all(b["hostname"] == hostname for b in old["bindings"].values())


@pytest.mark.parametrize(("role", "column"), [("device", "device_hostname"), ("source", "src_hostname"), ("destination", "dst_hostname")])
def test_unicode_hostname_roles_use_consistent_bound_comparison(profile, role, column):
    name = "Ä-İ-Σ-E\u0301-终端_A01"
    q = query(selector={"role": role, "kind": "hostname", "value": name})
    sql, params, _, fingerprint, _ = search_sql(profile, TENANT, q)
    assert name not in sql and f"lower({column})=%(value)s" in sql
    assert params["value"] == "Ä-İ-Σ-e\u0301-终端_a01"
    alternate = q.model_copy(update={"selector": q.selector.model_copy(update={"value": params["value"]})})
    assert search_sql(profile, TENANT, alternate)[3] == fingerprint
    validate_search_rows([row(**{column: name})], profile, TENANT, alternate, full=True)
    with pytest.raises(LakeReadError, match="lake_row_outside_bound_scope"):
        validate_search_rows([row(**{column: name.lower()})], profile, TENANT, alternate, full=True)


@pytest.mark.parametrize("hostname", ["终端 A", " 终端-A", "终端-A\n", "终端\x00A", "终端\u200bA", "终端/A", "终端'OR'1", "中"*254, ""])
def test_invalid_hostname_rejected_by_query_and_both_catalogs(profile, monkeypatch, hostname):
    with pytest.raises((LakeReadError, ValidationError)):
        search_sql(profile, TENANT, query(selector={"role": "device", "kind": "hostname", "value": hostname}))
    alert = SimpleNamespace(objects=[{"object_type": "host", "normalized_value": hostname, "id": "obj1"}])
    context = SimpleNamespace(alerts={"a": alert})
    for path in ("", str(PROFILE)):
        monkeypatch.setattr(settings, "SOCAI2_LAKE_QUERY_PROFILE_FILE", path)
        monkeypatch.setattr(settings, "CLICKHOUSE_DATABASE", profile.database)
        result = tools.catalog(context, TENANT)
        assert not result["bindings"] and len(result["omissions"]) == 1


def test_new_projection_device_is_not_source():
    projected = tools.row_projection(row(ocsf_json='{"class_uid":4001,"device":{"hostname":"Host-A"},"src_endpoint":{"hostname":"source-a"}}'))
    fields = {f["name"]: f["value"] for f in projected["fields"]}
    assert fields["device_hostname"] == "Host-A" and fields["src_hostname"] == "source-a"


@pytest.mark.parametrize("class_uid", [4001, 5001])
def test_device_display_name_and_hostname_are_distinct_attributes(class_uid):
    original = {"class_uid": class_uid, "device": {"name": "Business display name", "hostname": "Host-A"}}
    projected = tools.row_projection(row(class_uid=class_uid, ocsf_json=json.dumps(original)))
    fields = [f for f in projected["fields"] if f["name"] in {"device_name", "device_hostname"}]
    assert {(f["name"], f["value"], f["source_path"]) for f in fields} == {
        ("device_name", "Business display name", "$.ocsf_json.device.name"),
        ("device_hostname", "Host-A", "$.ocsf_json.device.hostname"),
    }
    assert not any(f["conflict"] for f in fields)
    assert 5001 not in tools.TOOLS.values()


def test_invalid_display_name_does_not_taint_hostname():
    original = {"class_uid": 5001, "device": {"name": {"unexpected": "object"}, "hostname": "Host-A"}}
    projected = tools.row_projection(row(class_uid=5001, ocsf_json=json.dumps(original)))
    host = [f for f in projected["fields"] if f["name"] == "device_hostname"]
    assert len(host) == 1 and host[0]["value"] == "Host-A" and not host[0]["conflict"]
    assert {"source_path": "$.ocsf_json.device.name", "reason": "unsupported_field_type"} in projected["omissions"]


def test_real_hostname_column_conflict_remains_separate_from_display_name():
    original = {"class_uid": 5001, "device": {"name": "Business display name", "hostname": "Host-A"}}
    projected = tools.row_projection(row(class_uid=5001, device_hostname="Host-B", ocsf_json=json.dumps(original)))
    host = [f for f in projected["fields"] if f["name"] == "device_hostname"]
    assert {(f["value"], f["source_path"]) for f in host} == {
        ("Host-A", "$.ocsf_json.device.hostname"), ("Host-B", "$.device_hostname"),
    }
    assert all(f["conflict"] for f in host)
    assert not next(f for f in projected["fields"] if f["name"] == "device_name")["conflict"]


@pytest.mark.parametrize("mapping_version", [None, ""])
def test_device_name_fix_preserves_legacy_projection(mapping_version):
    original = {"class_uid": 4001, "device": {"name": "Business display name", "hostname": "Host-A"}}
    saved = row(ocsf_json=json.dumps(original), mapping_version=mapping_version)
    if mapping_version is None:
        saved.pop("mapping_version")
    projected = tools.row_projection(saved)
    fields = [f for f in projected["fields"] if f["source_path"] in {
        "$.ocsf_json.device.name", "$.ocsf_json.device.hostname",
    }]
    assert len(fields) == 2 and all(f["conflict"] for f in fields)


def test_profile_missing_or_database_mismatch():
    for path, database in ((PROFILE, "other"), (PROFILE.with_name("not-found.json"), "aisoc")):
        with pytest.raises(LakeReadError) as raised:
            LakeQueryProfile.load(path, database=database)
        assert raised.value.state == "unavailable"
