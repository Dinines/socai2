"""Read the same completed execution with the corrected verifier; never dispatch."""
import argparse
import asyncio
import json
from pathlib import Path

from acceptance_clients import Http, Postgres, now, require
from acceptance_materials import control, read_json, save_report
from acceptance_runtime_contract import HttpConnection, PostgresConnection
from acceptance_session import load_execution
from acceptance_verify import verify_readback
from alert_scenarios import json_bytes, sha256


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    profile, session = load_execution(args.prepared)
    state = read_json(args.prepared / "runs/part1/state.json")
    require(state["status"] in {"completed", "completed_with_issues", "incomplete"}, "execution_not_terminal")
    require(state["stage"] == "saved_http_readback", "execution_not_ready_for_final_readback")
    http = Http(control(HttpConnection, read_json(Path(profile.connection_files.http)), "HTTP"), args.output / "http")
    pg = Postgres(control(PostgresConnection, read_json(Path(profile.connection_files.postgres)), "PG"), profile.tenant_id)
    alerts = [row["actual_alert_id"] for row in state["alerts"]]
    cases = [cid for values in state["cases"].values() for cid in values]
    try:
        identity = await pg.connect()
        before = await pg.snapshot(alerts, cases, full=True)
        require(all(t["state"] in {"completed", "failed", "skipped"} for t in before["analysis_tasks"]), "task_not_terminal")
        save_report(args.output / "saved-records.json", before)
        receipt = verify_readback(http, before)
        after = await pg.snapshot(alerts, cases, full=True)
        require(before == after, "scoped_saved_records_changed_during_readback")
        receipt.update(execution_id=session["execution"]["execution_id"], observed_at=now(), database=identity,
                       scoped_pg_readonly=before["readonly"] and after["readonly"],
                       scoped_pg_before_sha256=sha256(json_bytes(before)), scoped_pg_after_sha256=sha256(json_bytes(after)),
                       http_get_count=http.sequence, new_business_writes=0, new_model_calls=0)
        save_report(args.output / "readback.json", receipt)
        print(json.dumps({k: v for k, v in receipt.items() if k != "recorded_step_issues"}, ensure_ascii=False))
    finally:
        http.close()
        await pg.close()


if __name__ == "__main__":
    asyncio.run(main())
