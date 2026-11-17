"""Check actual lake-query rows against frozen business wires, without queries."""

import argparse
import json
from datetime import datetime
from pathlib import Path

E = Path(__file__).resolve().parent
CLASS = {"authentication_activity": 3002, "process_activity": 1007, "network_connections": 4001}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.snapshot.read_text())
    rows = data["rows"]
    manifest = json.loads((E / "batch/manifest.json").read_text())
    later = datetime.fromisoformat(json.loads((E / "S04-context-readback-01.json").read_text())["value"]["observed_at"])
    events = {}
    for phase in ("S01-context", "S04-context"):
        for item in manifest["phases"][phase]["records"]:
            wire = json.loads((E / "batch" / item["wire"]).read_text())
            events[wire["event_id"]] = {"phase": phase, "wire": wire}
    checks = []
    for artifact in rows["artifacts"]:
        result = artifact["content_json"]
        if artifact["kind"] != "tool_response" or not isinstance(result, dict) or result.get("contract_version") != "socai2.c4-lake.v1":
            continue
        assert result["state"] == "completed" and not result["truncated"]
        params = result["actual_args"]["parameters"]
        assert set(params) <= {"hostname", "query_id", "alert_ids", "tenant_id", "binding_id", "source_database"}, "additional query filter needs explicit checking"
        scope = result["actual_args"]["scope"]
        start, end = (datetime.fromisoformat(scope[k]) for k in ("window_start", "window_end"))
        phase = "S04" if datetime.fromisoformat(result["captured_at"]) >= later else "S01"
        expected = set()
        for eid, item in events.items():
            if item["phase"] == "S04-context" and phase == "S01":
                continue
            wire = item["wire"]
            ocsf = wire["ocsf_event"]
            if wire["tenant_id"] == params["tenant_id"] and ocsf["device"]["name"] == params["hostname"] and ocsf["class_uid"] == CLASS[result["tool_name"]] and start <= datetime.fromisoformat(ocsf["time"]) < end:
                expected.add(eid)
        actual = {row["event_id"] for row in result["rows"]}
        assert actual == expected and len(actual) == result["returned_rows"] == len(result["rows"])
        for row in result["rows"]:
            raw = row["ocsf_json"]
            raw = json.loads(raw) if isinstance(raw, str) else raw
            assert all(raw.get(k) == v for k, v in events[row["event_id"]]["wire"]["ocsf_event"].items())
        checks.append({"artifact_id": artifact["id"], "run_id": artifact["run_id"], "tool": result["tool_name"], "phase": phase, "window": {k: scope[k] for k in ("window_start", "window_end")}, "event_ids": sorted(actual), "status": "passed"})
    assert checks
    report = {"status": "passed", "queries": checks, "query_count": len(checks), "new_http_or_model_calls": 0, "unselected_tools": "not claimed as executed"}
    with args.output.open("x") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != "queries"}))


if __name__ == "__main__":
    main()
