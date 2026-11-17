"""Read completed batch records and verify final connection guard without new work."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "tools/testdata"))
from acceptance_append import connection_unchanged, idle, previous_unchanged
from acceptance_clients import Connections
from acceptance_session import load_execution


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


async def main(config_path):
    config = read(config_path)
    prepared = OUT / "prepared"
    first, last = prepared / "runs/part1", prepared / "runs/part2"
    states = [read(folder / "state.json") for folder in (first, last)]
    assert all(s["status"] in {"completed", "completed_with_issues"} for s in states)
    expected, rows = read(first / "saved-records.json"), read(last / "saved-records.json")
    previous_unchanged(expected, rows)
    assert idle(rows)
    old_hashes = read(OUT / "first-part-sha256-before-append.json")
    new_hashes = {str(p.relative_to(first)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in first.rglob("*") if p.is_file()}
    assert old_hashes == new_hashes
    profile, session = load_execution(prepared)
    live_output = OUT / "post-implementation-readback"
    live_output.mkdir()
    clients = Connections(profile, live_output)
    try:
        readiness = await clients.open()
        for folder in (first, last):
            connection_unchanged(read(folder / "preflight.json"), readiness)
        live = await clients.pg.snapshot([a["id"] for a in rows["alerts"]], [c["id"] for c in rows["cases"]], full=True)
        assert live == rows, "saved_records_changed_after_part2"
        save(live_output / "connection-binding.json", {"status": "passed", **readiness,
             "new_publications": 0, "new_business_writes": 0, "new_model_calls": 0,
             "note": "Final AP02 guard reads actual unchanged targets after the freeze02 live execution."})
        cids, result_ids = [UUID(c["id"]) for c in rows["cases"]], [UUID(r["id"]) for r in rows["results"]]
        async with clients.pg.connection.transaction(readonly=True):
            await clients.pg.connection.execute("SELECT set_config('app.current_tenant_id',$1,true)", profile.tenant_id)
            for table, column, ids in (("case_incidents", "case_id", cids), ("result_members", "result_id", result_ids)):
                raw = await clients.pg.connection.fetchval(
                    f"SELECT coalesce(json_agg(row_to_json(t) ORDER BY id),'[]'::json) FROM socai2.{table} t WHERE tenant_id=$1 AND {column}=ANY($2::uuid[])",
                    UUID(profile.tenant_id), ids)
                live[table] = json.loads(raw)
        save(OUT / "final-records.json", live)
    finally:
        await clients.close()
    exporter_path = ROOT / "docs/operations/evidence/streaming-fullflow-20261116-02/export-models.py"
    spec = importlib.util.spec_from_file_location("saved_model_export", exporter_path)
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    for artifact in rows["artifacts"]:
        content = artifact.get("content_json")
        if isinstance(content, dict) and isinstance(content.get("raw"), dict):
            raw = content["raw"]
            assert all(not choice.get("message", {}).get("reasoning_content") for choice in raw.get("choices", []))
    index = exporter.export(OUT / "final-records.json", OUT / "model-io",
        ["tenant_uid", "synthetic", "fixture", "is_test", "expected_verdict", config["execution_id"], profile.tenant_id])
    assert not any(x["input_observations"] for x in index["requests"])
    moments = []
    for attempt in rows["analysis_attempts"]:
        assert attempt["local_state"] == "ended" and attempt["local_ended_at"]
        moments += [(datetime.fromisoformat(attempt["started_at"]), 1),
                    (datetime.fromisoformat(attempt["local_ended_at"]), -1)]
    active = peak = 0
    for _, delta in sorted(moments):
        active += delta
        peak = max(active, peak)
    assert active == 0 and peak == 1
    diagnostics = []
    for artifact in rows["artifacts"]:
        content = artifact.get("content_json")
        if artifact["kind"] != "source_snapshot" or not isinstance(content, dict):
            continue
        keys = ("validation_review", "citation_review", "validation", "quality")
        detail = {k: content[k] for k in keys if k in content}
        if detail:
            diagnostics.append({"artifact_id": artifact["id"], "run_id": artifact["run_id"],
                                "schema_version": artifact["schema_version"], "details": detail})
    save(OUT / "retained-diagnostics.json", {"model_quality": "not_fully_evaluated", "artifacts": diagnostics,
         "recorded_step_issues": read(last / "readback.json")["recorded_step_issues"]})
    calls = index["requests"]
    summary = {"status": "passed", "execution_id": config["execution_id"],
        "parts": [{"part": s["part"], "status": s["status"], "sent": s["sent"], "execution_issues": s["execution_issues"]} for s in states],
        "counts": {k: len(v) for k, v in rows.items() if isinstance(v, list)},
        "first_part_files_unchanged": len(old_hashes), "previous_immutable_records": "unchanged",
        "post_readback_same_records": True, "configured_max_running_tasks": 1, "actual_attempt_concurrency_peak": peak,
        "active_attempts_at_end": active, "case_append": read(last / "append-readback.json"),
        "model_requests": len(calls), "model_finish_reasons": dict(Counter(r.get("finish_reason") for r in calls)),
        "usage_unknown_requests": index["usage_unknown_requests"],
        "total_tokens": sum(r["usage"]["total_tokens"] for r in calls if r.get("usage")),
        "input_metadata_observations": [], "model_quality": "not_fully_evaluated", "cost": "unknown",
        "runtime_source_freeze": "source-freeze-02.json", "final_AP02_guard": "post-implementation-readback/connection-binding.json"}
    save(OUT / "final-validation.json", summary)
    print(json.dumps({k: summary[k] for k in ("status", "counts", "first_part_files_unchanged", "actual_attempt_concurrency_peak", "model_requests", "model_finish_reasons", "total_tokens")}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    asyncio.run(main(parser.parse_args().config.resolve()))
