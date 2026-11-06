"""Freeze the three remaining synthetic scenarios against the verified 21 source snapshot."""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "deploy/local-investigation"))

from config import USER  # noqa: E402
from flow_fixture import encoded, prepare, sha  # noqa: E402

STATE = REPO / ".local"
PILOT = STATE / "deployed-pilot-20261106-01"
PILOT_EXPORT = PILOT / "exports/20261106T041629564912Z"
CONFIG = {"OPENAI_MODEL": "aisoc-investigation", "OPENAI_BASE_URL": "http://litellm:4000/v1",
          "SOCAI2_MODEL_PROTOCOL": "chat_completions", "SOCAI2_MODEL_SCHEMA_PROFILE": "vllm_grammar_v1"}
CARDS = (("02", "credential", "local-eval-20261106-02", "04:31"),
         ("03", "impact", "local-eval-20261106-03", "04:37"),
         ("04", "maintenance", "local-maintenance-20261105g", "04:43"))


def write_once(path, payload):
    body = encoded(payload) + b"\n"
    if path.exists():
        if path.read_bytes() != body:
            raise ValueError(f"frozen file changed: {path}")
    else:
        with path.open("xb") as stream:
            stream.write(body)
    return sha(body)


def previous_attempts():
    archive = (PILOT / "history-index.json").read_bytes()
    assert json.loads(archive)["model_attempts"] == 63
    manifest = json.loads((PILOT_EXPORT / "manifest.json").read_bytes())
    record = (PILOT_EXPORT / "database.json").read_bytes()
    assert sha(record) == next(s["sha256"] for s in manifest["sources"] if s["role"] == "database")
    steps = [s for s in json.loads(record)["run_steps"] if s["kind"] == "model" and s["state"] not in {"planned", "skipped"}]
    assert len(steps) == 3 and all(s["state"] == "completed" for s in steps)
    return {"model_attempts": 66, "archived_attempts": 63, "archive_sha256": sha(archive),
            "previous_pilot_attempts": 3, "previous_pilot_database_sha256": sha(record),
            "previous_pilot_step_ids": sorted(s["id"] for s in steps)}


def main():
    original = json.loads((PILOT / "plan.json").read_bytes())
    history = previous_attempts()
    assert sum(11 if scenario == "maintenance" else 7 for _, scenario, _, _ in CARDS) == 25
    all_ids = set(original["canonical_alert_ids"])
    for number, scenario, reference, minute in CARDS:
        name = "deployed-pilot-20261106-" + number
        folder = STATE / name
        folder.mkdir(exist_ok=True)
        plan, oracle = prepare("local-" + name, f"2026-11-06T{minute}:00+00:00",
                               backend="deployed", model_values=CONFIG, scenario=scenario)
        assert plan["model_profile"] == original["model_profile"]
        # Each case has its own user. Keep the account in file paths and raw mirrors consistent.
        case = json.loads(json.dumps(plan["case"]).replace("operator-0", "operator-" + str(int(number))))
        assert len(case["alerts"]) == len(case["events"]) == 2
        assert all(a["raw_event"] == e for a, e in zip(case["alerts"], case["events"]))
        assert all(json.loads(e["ocsf_event"]["raw_data"]) ==
                   {k:v for k,v in e["ocsf_event"].items() if k != "raw_data"} for e in case["events"])
        assert all_ids.isdisjoint(plan["canonical_alert_ids"])
        all_ids.update(plan["canonical_alert_ids"])
        attempts, runs = (11, 5) if scenario == "maintenance" else (7, 4)
        case.update(max_model_calls=attempts, max_runs=runs)
        history_hash = write_once(folder / "history-index.json", history)
        plan.update(case=case, actor_user_id=USER, campaign="deployed-matrix-20261106",
                    database="socai2_pilot_20261106_" + number, lake_database="socai2_next_validation",
                    topic_prefix="socai2.validation." + name, group="socai2-validation-" + name,
                    source_environment="21-isolated-deployed", comparison_batch_id=reference,
                    history_index_sha256=history_hash, previous_attempts=66, initial_cumulative_attempts=66,
                    additional_attempt_cap=25, global_local_model_call_cap=91, max_model_calls=attempts,
                    max_runs=runs, history_baseline_mode="immutable_66_plus_three_dedicated_db_attempt_counts",
                    source_sha256=original["source_sha256"],
                    transferred_source_manifest_sha256=original["transferred_source_manifest_sha256"])
        plan_hash = write_once(folder / "plan.json", plan)
        write_once(folder / "expected.json", oracle)
        print(name, scenario, plan_hash, history_hash)


if __name__ == "__main__":
    main()
