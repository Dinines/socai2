"""Prepare F1-F5 audit cards from saved passing batches; no database/model calls."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "saved-export"
SOURCES = [
    ("F1", "incident-case-scope-fix-20261115-01/pg-04"),
    ("F2", "case-input-metadata-fix-20261115-01/pg-01"),
    ("F3", "case-retry-fix-20261115-01/pg-03"),
    ("F4", "case-trigger-fix-20261115-01/test-pg-01"),
    ("F5", "execution-contract-fix-20261115-01/test-pg-01"),
]


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    loaded = []
    for label, source in SOURCES:
        folder = HERE.parent / source
        assert json.loads((folder / "result.json").read_text())["state"] == "passed", source
        loaded.append((label, folder, json.loads((folder / "snapshot.json").read_text())))
    OUT.mkdir(exist_ok=False)
    plan = {"batch": "stage7-audit-fixes-20261115-01-saved", "execution_class": "controlled_dependency", "cases": []}
    sources = []
    for label, folder, data in loaded:
        path = folder / "snapshot.json"
        sources.append({"path": str(path.relative_to(HERE.parent)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        for number, case in enumerate(data["cases"], 1):
            cid, key = case["id"], label.lower() + "-" + str(number)
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
            plan["cases"].append({"key": key, "case_id": cid,
                "title": "第7步 " + label + "（模型/查询替身，保留失败及未知）",
                "execution_class": "controlled_dependency", "real_model_calls": 0,
                "source_snapshot": str(path.relative_to(HERE.parent))})
            save(OUT / "readback" / key / "database.json", scoped)
    save(OUT / "plan.json", plan)
    save(OUT / "sources.json", sources)
    print(json.dumps({"state": "prepared_from_saved_snapshots", "cases": len(plan["cases"]), "new_model_calls": 0}))


if __name__ == "__main__":
    main()
