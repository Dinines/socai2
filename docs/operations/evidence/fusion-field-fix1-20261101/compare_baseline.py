"""Compare the committed baseline with this fix using local driver binding only."""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "services/fusion"))
from clickhouse_driver.block import RowOrientedBlock
from app.services import event_schema as current_schema, lake_writer as current_writer

BASE = "b400fd0"
source_files = ["services/fusion/app/services/event_schema.py", "services/fusion/app/services/lake_writer.py"]
baseline_hashes = []


def baseline_module(path, name):
    code = subprocess.check_output(["git", "-c", "safe.directory=E:/aisoc/socai2", "show", f"{BASE}:{path}"], cwd=ROOT)
    baseline_hashes.append({"path": path, "git_blob_sha256": hashlib.sha256(code).hexdigest()})
    module = ModuleType(name)
    sys.modules[name] = module
    exec(compile(code, f"{BASE}:{path}", "exec"), module.__dict__)
    return module


before_schema = baseline_module(source_files[0], "before_schema")
before_writer = baseline_module(source_files[1], "before_writer")
TENANT = "11111111-1111-1111-1111-111111111111"
EVENT = "abcdefab-cdef-abcd-efab-cdefabcdefab"
NORMAL = "22222222-2222-2222-2222-222222222222"


def message():
    return {"tenant_id": TENANT, "ocsf_event": {"metadata": {"uid": EVENT.upper()},
            "class_uid": 1007, "time": "2026-11-01T00:00:00Z", "process": {"name": "synthetic.exe"}}}


mapping = []
for location in ("event_id", "id", "metadata.uid"):
    payload = message()
    if location != "metadata.uid":
        payload[location] = EVENT.upper()
    if location == "event_id":
        payload["id"] = NORMAL
    mapping.append({"location": location,
        "before": {"alert_reference": before_schema.validate_raw_event(payload).source_event_id,
                   "lake_event_id": before_writer.event_to_row(payload)["event_id"]},
        "after": {"alert_reference": current_schema.validate_raw_event(payload).source_event_id,
                  "lake_event_id": current_writer.event_to_row(payload)["event_id"]}})


async def insert(module):
    errors, ids = [], []
    class Client:
        def execute(self, sql, rows, **kwargs):
            columns = sql.split("(", 1)[1].split(")", 1)[0].split(", ")
            try:
                RowOrientedBlock([(column, "String") for column in columns], deepcopy(rows), types_check=True)
            except Exception as exc:
                errors.append({"type": type(exc).__name__, "message": str(exc)})
                raise
            ids.extend(row.get("event_id") for row in rows)
    writer = module.LakeWriter(host="unused.invalid", batch_size=2)
    writer._client = Client()
    second = message()
    second["event_id"] = NORMAL
    accepted = [await writer.write_event(message()), await writer.write_event(second)]
    return {"write_event_returns": accepted, "metrics": writer.metrics(), "bound_ids": ids, "binding_errors": errors}


async def main():
    comparison = {"scope": "same synthetic inputs, actual local dict-row driver binding, no network/DB/Run/model",
        "baseline_commit": subprocess.check_output(["git", "-c", "safe.directory=E:/aisoc/socai2", "rev-parse", BASE], cwd=ROOT, text=True).strip(),
        "identity_mapping": mapping, "mixed_batch": {"before": await insert(before_writer), "after": await insert(current_writer)},
        "baseline_sources": baseline_hashes,
        "current_sources": [{"path": path, "sha256": hashlib.sha256((ROOT/path).read_bytes()).hexdigest()} for path in source_files]}
    Path(__file__).with_name("before-after.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"mapping_cases": len(mapping), "before_rows": comparison["mixed_batch"]["before"]["metrics"]["rows_written"],
        "after_rows": comparison["mixed_batch"]["after"]["metrics"]["rows_written"], "new_external_calls": 0}))


asyncio.run(main())
