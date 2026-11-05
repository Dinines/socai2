import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import context_fixture as fixture

ROOT = HERE.parents[1]


def test_context_envelopes_survive_real_writer_mapping_and_scope_controls():
    tenant = "53824f24-d1d4-5820-8147-f6cfda8a1247"
    case = {"key": "one", "host": "example-host", "window_start": "2026-11-05T00:00:00Z",
        "window_end": "2026-11-05T00:02:00Z", "alerts": [
            {"event_time": "2026-11-05T00:01:00Z", "raw_event": {"ocsf_event": {"actor": {"user": {"name": "operator"}}}}},
            {"raw_event": {"ocsf_event": {"src_endpoint": {"ip": "192.0.2.1"}, "dst_endpoint": {"ip": "198.51.100.1"}}}}]}
    events, oracle = fixture.build(run_id="context-test", tenant=tenant, case=case)
    assert (events, oracle) == fixture.build(run_id="context-test", tenant=tenant, case=case)
    assert len(events) == len({e["event_id"] for e in events}) == 10
    spec = importlib.util.spec_from_file_location("context_test_lake", ROOT / "services/fusion/app/services/lake_writer.py")
    lake = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lake)
    included = {i for ids in oracle["included"].values() for i in ids}
    start, end = (datetime.fromisoformat(case[k]) for k in ("window_start", "window_end"))
    for event in events:
        row = lake.event_to_row(event)
        assert str(row["event_id"]) == event["event_id"]
        observed = row["event_time"]
        observed = observed.replace(tzinfo=UTC) if observed.tzinfo is None else observed
        in_scope = row["src_hostname"] == case["host"] and start <= observed < end
        assert in_scope == (event["event_id"] in included)
        assert "expected" not in event and "control-" not in event["ocsf_event"]["raw_data"]
    assert len(included) == 7 and len(oracle["excluded"]) == 3
