"""Task 3a independent local receipt review; never sends business data."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
OWNER = ROOT / "docs/operations/evidence/acceptance-materials-20261117-01"
EXAMPLES = ROOT / "tools/testdata/acceptance-examples"
sys.path.insert(0, str(ROOT / "tools/testdata"))
import acceptance


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def snapshot(path):
    return {str(p.relative_to(path)): digest(p) for p in path.rglob("*") if p.is_file()}


def main():
    out = HERE / "run-01"
    out.mkdir(exist_ok=False)
    frozen = read(OWNER / "source-freeze-01.json")["sha256"]
    assert all(digest(ROOT / p) == h for p, h in frozen.items())
    inputs = read(OWNER / "source-inputs-01.json")
    sources = {name: ROOT / inputs[name]["source"] for name in ("streaming", "templates")}
    before = {name: snapshot(path) for name, path in sources.items()}
    assert all(before[name] == inputs[name]["sha256"] for name in sources)
    owner_before = snapshot(OWNER)
    profile = read(EXAMPLES / "profile.json")
    connections = {Path(p) for p in profile["connection_files"].values()}
    allowed = {p / "manifest.json" for p in sources.values()}
    for name, root in sources.items():
        recipe = read(EXAMPLES / f"{name}-conversion.json")
        allowed.update(root / f for p in recipe["parts"] for role in ("alerts", "context") for f in p[role])
    guarded = False
    observed_reads, forbidden_attempts = set(), []

    def audit(event, args):
        if not guarded:
            return
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec"}:
            forbidden_attempts.append(event)
            raise AssertionError(f"offline CLI attempted {event}")
        if event == "open" and isinstance(args[0], (str, bytes)):
            path = Path(args[0].decode() if isinstance(args[0], bytes) else args[0]).resolve()
            if path in connections:
                forbidden_attempts.append("connection_file_read")
                raise AssertionError("3a opened a connection configuration file")
            if any(path.is_relative_to(root.resolve()) for root in sources.values()):
                if path not in {p.resolve() for p in allowed}:
                    forbidden_attempts.append("historical_sidecar_read")
                    raise AssertionError("3a opened a historical control/answer sidecar")
                observed_reads.add(str(path.relative_to(ROOT)))

    sys.addaudithook(audit)
    calls = []

    def cli(label, args, expected=0):
        nonlocal guarded
        stdout = io.StringIO()
        guarded = True
        try:
            with redirect_stdout(stdout):
                code = acceptance.main(args)
        finally:
            guarded = False
        body = json.loads(stdout.getvalue())
        write(out / f"{label}-stdout.json", body)
        calls.append({"label": label, "entry": "acceptance.main argparse entry in process",
                      "argv": args, "exit_code": code, "expected_exit_code": expected})
        assert code == expected, (label, body)
        assert body["execution_status"] == "not_executed"
        return body

    packages = []
    for name, source in sources.items():
        target = out / name
        recipe_path = EXAMPLES / f"{name}-conversion.json"
        cli(name + "-convert", ["convert", "--source", str(source), "--recipe", str(recipe_path),
                                "--profile", str(EXAMPLES / "profile.json"), "--output", str(target)])
        report_path = out / f"{name}-inspection.json"
        cli(name + "-inspect", ["inspect", "--materials", str(target), "--profile",
                                str(EXAMPLES / "profile.json"), "--report", str(report_path)])
        plan = read(target / "plan.json")
        assert plan == read(report_path) == read(OWNER / f"{name}-inspection.json")
        assert plan == read(OWNER / "packages" / name / "plan.json")
        receipt = read(target / "conversion.json")
        owner_receipt = read(OWNER / "packages" / name / "conversion.json")
        assert receipt == owner_receipt
        manifest = read(source / "manifest.json")
        assert receipt["source_manifest_sha256"] == digest(source / "manifest.json")
        expected_sources = [f for p in read(recipe_path)["parts"] for role in ("alerts", "context") for f in p[role]]
        assert set(receipt["source_files"]) == set(expected_sources)
        hashes = manifest["inputs"] if name == "streaming" else {r["payload"]: r["payload_sha256"] for r in manifest["records"]}
        checked = []
        for origin in receipt["records"]:
            original_path = source / origin["source"]
            raw = original_path.read_bytes()
            original = json.loads(raw.splitlines()[origin["source_line"] - 1] if origin["source_line"] else raw)
            converted_path = target / origin["target"]
            converted = read(converted_path)
            assert all(key in converted and converted[key] == value for key, value in original.items())
            added = set(converted) - set(original)
            assert added == set(origin["added_identity_fields"]) <= {"identity_version", "source_alert_id"}
            if added:
                assert converted["identity_version"] == "source-v1" and converted["source_alert_id"] == original["id"]
            assert digest(original_path) == hashes[origin["source"]] == origin["source_sha256"]
            assert digest(converted_path) == origin["target_sha256"] == plan["material_sha256"][origin["target"]]
            assert converted_path.read_bytes() == (OWNER / "packages" / name / origin["target"]).read_bytes()
            checked.append({"source": origin["source"], "line": origin["source_line"],
                            "target": origin["target"], "source_sha256": digest(original_path),
                            "target_sha256": digest(converted_path), "all_original_fields_equal": True,
                            "added_identity_fields": sorted(added)})
        expected_counts = [{"alerts": 3, "context": 12}, {"alerts": 1, "context": 1}] if name == "streaming" else [{"alerts": 2, "context": 0}]
        assert [p["counts"] for p in plan["parts"]] == expected_counts
        assert plan["selected_part"] == "part1" and not plan["selection_required"]
        assert [p["selected"] for p in plan["parts"]] == ([True, False] if name == "streaming" else [True])
        assert all(p["execution_status"] == "not_executed" for p in plan["parts"])
        assert plan["execution_identity"] == "requires_new_execution_identity"
        assert plan["connection_status"] == "not_checked" and plan["time_policy"] == "preserved"
        assert plan["business_connections"] == plan["kafka_sends"] == plan["model_calls"] == 0
        if name == "streaming":
            cases = plan["scenario"]["cases"]
            assert [(c["scope"], c["alert_refs"], c["create_after_part"], c["check_after_parts"]) for c in cases] == [
                ("incident", ["part1/alerts/001.json"], "part1", ["part2"]),
                ("alerts", ["part1/alerts/001.json"], "part1", ["part2"])]
            assert [[a["action"] for a in p["case_actions"]] for p in plan["parts"]] == [["create", "create"], ["check", "check"]]
            for p in plan["parts"]:
                for link in p["source_links"]:
                    context = read(target / link["context"])
                    assert link["source_event_id"] == context["event_id"]
                    assert link["material_status"] == "provided_not_ingested"
            assert [len(p["source_links"]) for p in plan["parts"]] == [3, 1]
        else:
            assert plan["scenario"]["cases"] == []
            assert not (target / "part1/context").exists()
            assert sum(len(read(p)["raw_event"]["telemetry"]) for p in (target / "part1/alerts").glob("*.json")) == 5
            assert plan["parts"][0]["context_query_verification"] == "not_covered"
        packages.append({"name": name, "counts": expected_counts, "record_checks": checked,
                         "independent_plan_equals_owner_saved_plan": True, "originals_equal": True})

    # One small changed copy: absent part1, explicit selection and numeric order.
    variant = out / "no-part1"
    shutil.copytree(out / "templates", variant)
    (variant / "part1").rename(variant / "part7")
    scenario = copy.deepcopy(read(variant / "scenario.json"))
    scenario["parts"][0]["id"] = "part7"
    (variant / "scenario.json").write_text(json.dumps(scenario))
    (variant / "part7/alerts/001.json").rename(variant / "part7/alerts/10.json")
    (variant / "part7/alerts/002.json").rename(variant / "part7/alerts/2.json")
    args = ["inspect", "--materials", str(variant), "--profile", str(EXAMPLES / "profile.json")]
    result = cli("no-part1", [*args, "--report", str(out / "no-part1-inspection.json")])
    assert result["selected_part"] is None and result["selection_required"]
    plan = read(out / "no-part1-inspection.json")
    assert plan["parts"][0]["files"]["alerts"] == ["part7/alerts/2.json", "part7/alerts/10.json"]
    assert not plan["parts"][0]["selected"]
    result = cli("explicit-part7", [*args, "--part", "part7", "--report", str(out / "explicit-part7-inspection.json")])
    assert result["selected_part"] == "part7" and not result["selection_required"]
    assert snapshot(OWNER) == owner_before
    assert all(snapshot(path) == before[name] for name, path in sources.items())
    assert all(digest(ROOT / p) == h for p, h in frozen.items())
    assert not forbidden_attempts
    write(HERE / "independent-review-01.json", {
        "scope": "task3a_offline_material_entry_only", "status": "passed", "blocking_findings": [],
        "source_sha256": frozen, "source_freeze_files_equal": len(frozen), "packages": packages,
        "calls": calls, "boundary_copy": "run-01/no-part1", "numeric_order": [2, 10],
        "no_part1_selection_required": True, "explicit_part7_remains_not_executed": True,
        "offline_guard": {"mechanism": "Python audit hook around in-process CLI calls",
                          "network_or_process_or_forbidden_read_attempts": forbidden_attempts,
                          "source_reads": sorted(observed_reads)},
        "source_inputs_and_owner_evidence_unchanged": True,
        "not_verified": ["new execution identities/time mapping", "actual connection readiness",
                         "Kafka/lake/PG/HTTP processing", "real model execution or quality",
                         "interactive append", "Docker build/run", "task3 overall/change audit"],
    })
    print("Independent 3a review passed: 16 frozen files, 19 records, 6 offline CLI calls; originals unchanged.")


if __name__ == "__main__":
    main()
