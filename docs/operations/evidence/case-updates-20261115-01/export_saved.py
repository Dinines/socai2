"""Prepare archive cards from saved, verified snapshots; no database or model calls."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "saved-export"
OUT.mkdir(exist_ok=False)
plan = {"batch": "case-updates-20261115-01-saved", "execution_class": "controlled_dependency", "cases": []}
sources = []


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


for source in ("read-7a-01", "read-7b-03", "lifecycle-02"):
    path = HERE / source / "snapshot.json"
    data = json.loads(path.read_text())
    sources.append({"path": str(path.relative_to(HERE)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    for number, case in enumerate(data["cases"], 1):
        cid = case["id"]
        key = source + "-" + str(number)
        run_ids = {r["id"] for r in data["runs"] if r.get("case_id") in (None, cid)}
        scoped = {}
        for table, rows in data.items():
            if table == "cases":
                scoped[table] = [case]
            elif table == "runs":
                scoped[table] = [r for r in rows if r["id"] in run_ids]
            elif table in {"analysis_tasks", "analysis_attempts", "analysis_subject_state"}:
                scoped[table] = [r for r in rows if r.get("subject_type") != "case" or r["subject_id"] == cid]
            else:
                scoped[table] = [r for r in rows if r.get("case_id") in (None, cid)
                    and (r.get("run_id") is None or r["run_id"] in run_ids)]
        plan["cases"].append({"key": key, "case_id": cid, "title": "第7步 " + source + "（模型与查询替身）",
            "execution_class": "controlled_dependency", "real_model_calls": 0})
        save(OUT / "readback" / key / "database.json", scoped)
save(OUT / "plan.json", plan)
save(OUT / "sources.json", sources)
print(json.dumps({"state": "prepared_from_saved_snapshots", "cases": len(plan["cases"]), "new_model_calls": 0}))
