"""Reuse the existing read transports for three affected production reads only."""
import json
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "docs/operations"), str(ROOT / "services/api")]
from production_case_probe import query, save
from verify_current_release import fetch

folder = Path(__file__).resolve().parent
cfg = json.loads((folder / "production-read-config.json").read_text())
case = str(UUID(cfg["case_id"]))
sql = f"""WITH chosen AS (
 SELECT * FROM socai2.results WHERE case_id='{case}' ORDER BY created_at DESC,id DESC LIMIT 1
) SELECT jsonb_build_object(
 'case',(SELECT to_jsonb(c) FROM socai2.cases c WHERE c.id='{case}'),
 'result',(SELECT to_jsonb(r) FROM chosen r),
 'run',(SELECT to_jsonb(r) FROM socai2.runs r WHERE r.id=(SELECT source_run_id FROM chosen))
);"""
before = query(cfg, sql)
save(folder / "production-read-before.json", before)
result, run = before["result"], before["run"]
base = f"/api/v1/socai2/cases/{case}"
paths = [base, base + "/runs/" + run["id"], base + "/results/" + result["id"]]
responses = fetch(cfg, [{"path": p, "method": "GET"} for p in paths], cfg["http"])
save(folder / "production-reads.json", responses)
assert all(r["status"] == 200 for r in responses)
read = responses[-1]["body"]["result"]
fields = ("conclusion", "conclusion_state", "validation_state", "findings", "questions", "recommendations")
assert all(read[k] == result[k] for k in fields)
after = query(cfg, sql)
save(folder / "production-read-after.json", after)
assert before == after
save(folder / "production-readback.json", {"release": cfg["release"], "case_id": case,
    "run_id": run["id"], "result_id": result["id"], "http_reads": len(responses),
    "affected_result_fields_match": list(fields), "snapshot_unchanged": True,
    "database_writes": 0, "model_calls": 0, "scope": cfg["scope"]})
print(json.dumps({"http_reads": len(responses), "fields_match": len(fields), "snapshot_unchanged": True}))
