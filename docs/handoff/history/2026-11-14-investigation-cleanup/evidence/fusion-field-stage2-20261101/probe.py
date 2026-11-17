"""Bounded local observations of received events -> lake mapping -> Case Tool.

Synthetic inputs, actual mapping/driver column-binding/Tool functions, and
read-only reuse of the already exported r13 evidence. No services are started
or called. Assertions describe current behaviour, not acceptance of defects.
"""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
from importlib.metadata import version
import json
from pathlib import Path
import sys
from unittest.mock import patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]

def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

lake = load("audit_stage2_lake", "services/fusion/app/services/lake_writer.py")
schema = load("audit_stage2_schema", "services/fusion/app/services/event_schema.py")
sessions = load("audit_stage2_sessions", "services/fusion/app/services/sessions.py")
sys.path.insert(0, str(ROOT / "services/api"))
from app.investigation_v2 import case_analysis_tools as tools
from app.db.clickhouse import LakeQueryResult
from clickhouse_driver.block import RowOrientedBlock

TENANT = str(UUID(int=1))
EVENT = "abcdefab-cdef-abcd-efab-cdefabcdefab"
BASE = {"id": EVENT, "tenant_id": TENANT, "ocsf_event": {
    "class_uid": 1007, "category_uid": 1, "severity_id": 2,
    "time": "2026-10-31T09:02:03+08:00", "device": {"name": "synthetic-host"},
    "src_endpoint": {"ip": "192.0.2.1", "port": 12345},
    "dst_endpoint": {"ip": "192.0.2.2", "port": 443}, "protocol": "TCP",
    "actor": {"user": {"name": "synthetic-user"}}, "process": {"name": "synthetic.exe"},
    "file": {"path": "C:/synthetic.exe", "fingerprints": [{"algorithm": "SHA256", "value": "a" * 64}]},
    "raw_data": '{"synthetic":true}',
}}
observations = []

def observe(name, condition, **actual):
    assert condition, name
    observations.append({"name": name, "current_behaviour_confirmed": True, **actual})

def refs(source_id, event_id):
    return tools.source_alignment({"tool": "process_activity", "available": True, "rows": [{"event_id": event_id}]},
        {"evidence": [{"kind": "alert", "evidence_id": "A1", "data": {"source_event_ids": [source_id]}}]})["row_alert_refs"]

row = lake.event_to_row(BASE)
observe("supported_fields_and_utc", row["event_id"] == schema.validate_raw_event(BASE).source_event_id == EVENT
    and row["event_time"] == datetime(2026, 10, 31, 1, 2, 3) and row["tenant_id"] == TENANT
    and row["process_name"] == "synthetic.exe" and row["class_uid"] == 1007
    and row["dst_port"] == 443 and refs(EVENT, row["event_id"]) == [["A1"]],
    utc=row["event_time"].isoformat(), exact_refs=refs(EVENT, row["event_id"]))
both = deepcopy(BASE); both["event_id"] = str(UUID(int=102))
source_id = schema.validate_raw_event(both).source_event_id
observe("different_id_precedence", source_id != lake.event_to_row(both)["event_id"],
    alert_uses="event_id", lake_uses="id", refs=refs(source_id, lake.event_to_row(both)["event_id"]))
upper = deepcopy(BASE); upper["id"] = EVENT.upper()
observe("same_uuid_text_not_normalized_for_alignment", UUID(schema.validate_raw_event(upper).source_event_id) == UUID(lake.event_to_row(upper)["event_id"])
    and refs(schema.validate_raw_event(upper).source_event_id, lake.event_to_row(upper)["event_id"]) == [[]])
metadata = deepcopy(BASE); metadata.pop("id"); metadata["ocsf_event"]["metadata"] = {"uid": EVENT}
observe("valid_metadata_uuid_not_used_by_lake", schema.validate_raw_event(metadata).source_event_id == EVENT and lake.event_to_row(metadata)["event_id"] is None)

activity = {"actor": {"kind": "human", "id": "synthetic-user"}, "action": "process.start", "outcome": "success",
    "session": {"id": str(UUID(int=301)), "key": "synthetic-session", "key_kind": "vendor_session"}}
top = deepcopy(BASE); top["activity"] = activity
toprow = lake.event_to_row(top)
observe("top_activity_recognized_by_session_but_dropped_by_lake", activity["session"]["key_kind"] in sessions.KEY_KINDS and sessions._session_block(top) == activity["session"]
    and all(toprow[k] == "" for k in ["action", "outcome", "session_id", "actor_id"]),
    action=toprow["action"], outcome=toprow["outcome"], session_id=toprow["session_id"])
nested = deepcopy(BASE); nested["ocsf_event"]["activity"] = activity
observe("nested_activity_lands_but_session_reader_misses_it", lake.event_to_row(nested)["session_id"] == activity["session"]["id"] and sessions._session_block(nested) is None)
hashes = deepcopy(BASE); hashes["ocsf_event"]["file"]["fingerprints"].insert(0, {"algorithm": "MD5", "value": "b" * 32})
observe("first_hash_mislabeled_sha256", lake.event_to_row(hashes)["hash_sha256"] == "b" * 32,
    supplied_sha256_preserved_in_raw=True, projected_hash_length=32)
large = deepcopy(BASE); large["ocsf_event"]["raw_data"] = "SYNTHETIC:" + "x" * 300000
large_row = lake.event_to_row(large)
try:
    json.loads(large_row["ocsf_json"]); valid_json = True
except json.JSONDecodeError:
    valid_json = False
observe("raw_cut_without_disclosure", len(large_row["raw_payload"]) == 65536 and len(large_row["ocsf_json"]) == 262144
    and not valid_json and not any("trunc" in k for k in large_row), ocsf_json_valid=valid_json,
    raw_payload_chars=len(large_row["raw_payload"]), ocsf_json_chars=len(large_row["ocsf_json"]))
raw_dict = deepcopy(BASE); raw_dict["ocsf_event"]["raw_data"] = {"synthetic": True}
dict_row = lake.event_to_row(raw_dict)
observe("raw_dict_stringified_as_python_repr", dict_row["raw_payload"] == "{'synthetic': True}"
    and json.loads(dict_row["ocsf_json"])["raw_data"] == {"synthetic": True},
    note="Short original dict survives in ocsf_json; raw_payload alone is not JSON.")

class ColumnBindingOnly:
    """Use the actual local driver binder, never connect or serialize to a server."""
    def __init__(self):
        self.error = None
    def execute(self, sql, rows, **kwargs):
        try:
            RowOrientedBlock(columns_with_types=[(name, "String") for name in lake._COLUMNS], data=rows, types_check=True)
        except KeyError as exc:
            self.error = str(exc)
            raise

async def check_calls():
    writer = lake.LakeWriter(host="unused.invalid", batch_size=2)
    binding = ColumnBindingOnly(); writer._client = binding
    one = await writer.write_event(deepcopy(BASE))
    two = await writer.write_event(metadata)
    observe("valid_metadata_id_causes_fixed_column_binding_failure", one and two and binding.error == "'event_id'"
        and writer.rows_written == 0 and writer.flush_failures == 1 and writer.metrics()["buffered"] == 0,
        driver_version=version("clickhouse-driver"), error=binding.error, affected_batch_rows=2,
        write_event_returns=[one, two], rows_written=writer.rows_written, buffered=writer.metrics()["buffered"])
    captured = []
    async def query(sql, **kwargs):
        captured.append({"sql": sql, "params": kwargs["params"]})
        columns = sql.split("SELECT ", 1)[1].split(" FROM", 1)[0].split(", ")
        values = [row.get(k) for k in columns]
        return LakeQueryResult(columns=columns, rows=[values, values], row_count=2, elapsed_ms=0)
    start = datetime.fromisoformat("2026-10-31T09:00:00+08:00")
    end = datetime.fromisoformat("2026-10-31T09:04:00+08:00")
    tool = tools.CaseTools(UUID(TENANT), ["synthetic-host"], start, end)
    with patch.object(tools.settings, "AISOC_DISABLE_CLICKHOUSE", False), patch.object(tools.settings, "CLICKHOUSE_HOST", "unused.invalid"), patch.object(tools, "execute_lake_query", query):
        process = await tool.execute("process_activity", {"hostname": "synthetic-host", "limit": 1})
        await tool.execute("network_connections", {"hostname": "synthetic-host", "limit": 2})
    observe("tool_query_keeps_scope_and_categories", len(captured) == 2
        and "class_uid = 1007 AND process_name != ''" in captured[0]["sql"] and "class_uid = 4001" in captured[1]["sql"]
        and all("tenant_id = %(tenant_id)s AND src_hostname = %(hostname)s" in c["sql"] for c in captured)
        and captured[0]["params"]["start"] == "2026-10-31 01:00:00.000000" and captured[0]["params"]["fetch_limit"] == 2,
        note="Actual Tool SQL generated; substitute returns rows, SQL not executed against ClickHouse.")
    observe("duplicate_rows_consume_tool_limit", process["available"] and process["truncated"] and process["returned_count"] == 1
        and all(" DISTINCT " not in c["sql"] and " FINAL" not in c["sql"] and " BY event_id" not in c["sql"] for c in captured),
        input_rows=2, unique_event_ids=1, output_rows=process["returned_count"], truncated=process["truncated"])

asyncio.run(check_calls())

# Reuse exported r13 observations; do not start another Run or query.
old = ROOT / "docs/operations/evidence/investigation-r13-20261101"
proof = json.loads((old / "query-and-cost-proof.json").read_text(encoding="utf-8"))
finishes = {v["query_id"]: v for v in proof["query_log"] if v["type"] == "QueryFinish"}
history = []
for group in ["A", "B"]:
    context = {"evidence": [{"kind": "alert", "evidence_id": f"A{i}", "data": {
        "source_event_ids": json.loads((old / f"{group}-A{i}.response.txt").read_text(encoding="utf-8"))["source_event_ids"]}} for i in [1, 2]]}
    for filename in ["010-step-5.response.txt", "014-step-9.response.txt"]:
        value = json.loads((old / group / filename).read_text(encoding="utf-8"))["data"]["evidence"]
        finish = finishes[value["query_id"]]
        history.append({"case_group": group, "tool": value["tool"], "rows": len(value["rows"]),
            "query_finish_rows": finish["result_rows"], "exception_code": finish["exception_code"],
            "exact_refs": tools.source_alignment(value, context)["row_alert_refs"]})
observe("existing_r13_query_evidence_reused", [v["rows"] for v in history] == [1, 1, 0, 0]
    and all(v["rows"] == v["query_finish_rows"] and v["exception_code"] == 0 for v in history),
    note="Historical real queries; positive rows are manual fixture evidence, not proof of Fusion ingestion.")
paths = ["services/fusion/app/services/" + p for p in ["lake_writer.py", "event_schema.py", "sessions.py"]]
paths += ["services/fusion/app/workers/consumer.py", "services/api/app/investigation_v2/case_analysis_tools.py", "services/api/clickhouse/001_init.sql"]
output = {"scope": "local synthetic mapping, local driver column binding, substituted Tool reads, saved r13 evidence",
    "new_business_calls": 0, "new_model_calls": 0, "live_acceptance": False, "observations": observations,
    "historical_queries": history, "source_sha256": {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}
Path(__file__).with_name("observations.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"observations_confirmed": len(observations), "new_business_calls": 0, "historical_query_references": history}, ensure_ascii=False))
