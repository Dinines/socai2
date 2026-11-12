"""Export the exact program-built inputs from the existing direct field check.

Query rows are synthetic; this preview is not a live model execution.
"""
import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
FOLDER = Path(__file__).parent
config = json.loads((FOLDER / "config.json").read_text())
sys.path[:0] = [str(ROOT / p) for p in (".", "services/api", "services/api/tests")]
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])
import test_socai2_case_followup_boundary as tests
from app.socai2 import runtime_policy

runtime_policy.active_policy.cache_clear()
policy = runtime_policy.active_policy()
sample = tests.base_tests.sample.__wrapped__(policy)
build = tests.inputs.build
captured = {}


def capture(stage, *args, **kwargs):
    prepared = build(stage, *args, **kwargs)
    if kwargs.get("previous") and len(kwargs.get("projections", [])) == 2:
        captured[stage] = (copy.deepcopy(prepared), copy.deepcopy(kwargs["projections"]))
    return prepared


def save(name, value):
    body = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path = FOLDER / name
    assert not path.exists(), "Do not overwrite completed preview evidence."
    path.write_text(body)
    return hashlib.sha256(body.encode()).hexdigest()


with patch.object(tests.inputs, "build", capture):
    getattr(tests, config["test"])(sample)
assert set(captured) == {"Deep", "C6"}
summary = {**config, "database_calls": 0, "http_calls": 0, "profile": policy.case_io.identity, "stages": {}}
for stage, (prepared, projections) in captured.items():
    body = prepared["messages"][1]["content"]
    rows = {r["id"]: r for r in prepared["followup_boundary"]["records"] if r["block"] == "query"}
    groups = [g for g in prepared["followup_boundary"]["presentation"]["groups"] if g[0] in rows]
    excerpt, heading, printed_heading = [], None, None
    for line in body.splitlines():
        if "｜原范围=" in line and line.startswith("["):
            heading = line
        if any(f"[{sid}]" in line for sid in rows):
            if heading != printed_heading:
                excerpt.append(heading)
                printed_heading = heading
            excerpt.append(line)
    files = {stage + "-model-input.txt": body, stage + "-tool-results.txt": "\n".join(excerpt) + "\n",
             stage + "-selection.json": {k: prepared[k] for k in
                ("source_map", "case_boundary", "followup_boundary", "omissions")}}
    hashes = {name: save(name, value) for name, value in files.items()}
    summary["stages"][stage] = {"input_characters": len(body), "query_count": len(projections),
        "query_record_count": sum(len(p["content_json"]["rows"]) for p in projections),
        "original_query_fields": sum(q["projected_fields"] for q in prepared["followup_boundary"]["query_facts"]),
        "visible_query_sources": len(rows), "query_display_groups": len(groups),
        "excluded_identity_fields": sum(o["reason"] == "query_identity_kept_in_backend" for o in prepared["omissions"]),
        "all_dependencies_visible": all(d["visible_id"] for d in prepared["followup_boundary"]["dependencies"]),
        "file_sha256": hashes}
save("synthetic-query-projections.json", captured["C6"][1])
summary["source_sha256"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
    "services/api/app/socai2/case_followup_input.py", "services/api/app/socai2/case-input-v1.json",
    "services/api/tests/test_socai2_case_followup_boundary.py")}
save("summary.json", summary)
print(json.dumps(summary["stages"], ensure_ascii=False, indent=2))
