"""Independent offline report review over the completed 21 session."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import sys
from contextlib import ExitStack, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/testdata"))
from acceptance import main
from acceptance_report_links import ReportConfig, add_workbench_links

BASE = ROOT / "docs/operations/evidence/acceptance-fullflow-21-20261117-01"
OWNER = ROOT / "docs/operations/evidence/workbench-deeplink-20261117-01"
PREPARED = BASE / "results/prepared"
OUT = Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=False)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(value):
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()
                if k not in {"observed_at", "workbench", "viewer_url"}}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return value


checks = []
attempts = {"network": 0, "connection_config_read": 0, "business_execute": 0}
old = read(BASE / "results/report-01/report.json")
config = read(OWNER / "report-config.json")
originals = read(BASE / "results-copy.json")["sha256"]
original_report_sources = ["tools/testdata/acceptance.py", "tools/testdata/acceptance_console.py",
                           "tools/testdata/acceptance_report.py", "tools/testdata/acceptance_report_render.py",
                           "tools/testdata/acceptance_report_links.py"]
code_before = {p: sha(ROOT / p) for p in original_report_sources}
assert all(sha(BASE / p) == h for p, h in originals.items())
connections = set(read(PREPARED / "session.json")["profile"]["connection_files"].values())
real_open = Path.open


def guarded_open(path, *args, **kwargs):
    if str(path) in connections:
        attempts["connection_config_read"] += 1
        raise AssertionError("report opened a connection configuration")
    return real_open(path, *args, **kwargs)


def forbidden(kind):
    def reject(*args, **kwargs):
        attempts[kind] += 1
        raise AssertionError(f"unexpected {kind}")
    return reject


def check(name, fn):
    try:
        details = fn()
    except Exception as exc:
        checks.append({"name": name, "status": "failed", "error": str(exc), "type": type(exc).__name__})
    else:
        checks.append({"name": name, "status": "passed", "details": details})


def verify_export(path, expected_config):
    report, manifest = read(path / "report.json"), read(path / "manifest.json")
    assert normalize(report) == normalize(old), "saved facts/quality changed"
    assert manifest["workbench"] == report["workbench"]
    assert report["workbench"] == ({"configured": True, **expected_config}
                                    if expected_config else {"configured": False})
    assert all(sha(path / row["path"]) == row["sha256"] for row in manifest["files"])
    markdown = (path / "report.md").read_text()
    actual = []
    for subject in report["subjects"]:
        for run in subject["rounds"]:
            if expected_config is None:
                assert "viewer_url" not in run
                continue
            link = run["viewer_url"]
            parsed = urlsplit(link)
            assert parsed.netloc == urlsplit(expected_config["workbench_url"]).netloc
            assert parsed.path == urlsplit(expected_config["workbench_url"]).path
            assert parse_qs(parsed.query, strict_parsing=True) == {
                "subject_type": [subject["kind"]], "subject_id": [subject["id"]],
                "run_id": [run["run_id"]], "environment": [expected_config["workbench_environment_label"]]}
            assert f"[在工作台打开第 {run['round']} 轮]({link})" in markdown
            actual.append((subject["kind"], subject["id"], run["run_id"]))
    if expected_config:
        assert len(actual) == len(set(actual)) == 6
    else:
        assert "未配置工作台地址" in markdown
    exports = [p for p in (path / "models").rglob("*") if p.is_file()]
    assert len(exports) == 24
    assert all(p.read_bytes() == (BASE / "results/report-01" / p.relative_to(path)).read_bytes()
               for p in exports), "messages/schema/original outputs changed"
    assert not any(report["this_command"].values())
    return {"actual_links": actual, "model_export_files_unchanged": len(exports),
            "report_facts_equal_to_old": True, "manifest_readback": "passed"}


def cli_report(configured):
    output = OUT / ("report-configured" if configured else "report-unconfigured")
    args = ["report", "--prepared", str(PREPARED), "--output", str(output)]
    if configured:
        args += ["--report-config", str(OWNER / "report-config.json")]
    with redirect_stdout(io.StringIO()):
        assert main(args) == 0
    return verify_export(output, config if configured else None)


def cli_menu():
    answers = iter(["report", "quit"])
    with patch("builtins.input", side_effect=lambda _: next(answers)), redirect_stdout(io.StringIO()):
        assert main(["session", "--prepared", str(PREPARED), "--output", str(OUT / "console"),
                     "--report-config", str(OWNER / "report-config.json")]) == 0
    return verify_export(OUT / "console/reports/0001", config)


def rejects_wrong_environment():
    path = OUT / "wrong-source-config.json"
    path.write_text(json.dumps({**config, "source_environment_label": "other environment"}))
    with redirect_stdout(io.StringIO()):
        assert main(["report", "--prepared", str(PREPARED), "--output", str(OUT / "rejected-report"),
                     "--report-config", str(path)]) == 2
    assert not (OUT / "rejected-report").exists()
    return {"rejected_before_export": True}


def no_run():
    # Explicit controlled in-memory shape: accepted subject with no saved Run.
    value = {"environment": old["environment"], "subjects": [
        {"kind": "case", "id": old["subjects"][0]["id"], "rounds": []}]}
    add_workbench_links(value, ReportConfig.model_validate(config))
    assert value["subjects"][0]["rounds"] == [] and "viewer_url" not in json.dumps(value)
    return {"fixture_kind": "controlled_in_memory_no_run", "links": 0}


def addresses():
    for url in ["file:///viewer/", "https://name:secret@host/viewer/", "http://host/viewer/?x=1",
                "http://host/viewer/#run", "http://host/viewer/?", "http://host:99999/viewer/"]:
        try:
            ReportConfig.model_validate({**config, "workbench_url": url})
        except ValueError:
            continue
        raise AssertionError("invalid configured address accepted")
    return {"invalid_configurations_rejected": 6}


def ipv6():
    address = "http://[::1]:4177/viewer/"
    cfg = ReportConfig.model_validate({**config, "workbench_url": address})
    report = copy.deepcopy(old)
    add_workbench_links(report, cfg)
    link = report["subjects"][0]["rounds"][0]["viewer_url"]
    parsed = urlsplit(link)
    assert (parsed.hostname, parsed.port) == ("::1", 4177), link
    return {"accepted_address_preserved": address}


with ExitStack() as stack:
    stack.enter_context(patch("pathlib.Path.open", guarded_open))
    stack.enter_context(patch("socket.socket", side_effect=forbidden("network")))
    stack.enter_context(patch("socket.create_connection", side_effect=forbidden("network")))
    stack.enter_context(patch("acceptance_console.execute_part", side_effect=forbidden("business_execute")))
    check("owner_saved_report", lambda: verify_export(OWNER / "report-01", config))
    check("independent_report_cli", lambda: cli_report(True))
    check("unconfigured_old_session", lambda: cli_report(False))
    check("session_cli_menu_wiring", cli_menu)
    check("wrong_source_environment_rejected", rejects_wrong_environment)
    check("no_run_no_fabricated_link", no_run)
    check("plain_http_address_contract", addresses)
    check("ipv6_address_preserved", ipv6)

unchanged = all(sha(BASE / p) == h for p, h in originals.items())
code_after = {p: sha(ROOT / p) for p in original_report_sources}
result = {"status": "passed" if all(c["status"] == "passed" for c in checks) and unchanged
          and code_before == code_after and not any(attempts.values()) else "needs_review",
          "observed_at": datetime.now(timezone.utc).isoformat(), "scope": "report_exit_only",
          "checks": checks, "guard_attempts": attempts,
          "original_files": len(originals), "originals_unchanged": unchanged,
          "source_sha256_before": code_before, "source_sha256_after": code_after,
          "source_stable_during_review": code_before == code_after,
          "new_model_calls": 0, "new_ingress": 0, "business_writes": 0, "deployments": 0,
          "not_verified": ["browser exact navigation", "live capabilities agreement", "new release on 21",
                           "model content quality", "D5/D6"]}
(OUT / "independent-report-review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"status": result["status"], "checks": [(r["name"], r["status"]) for r in checks],
                  "guard_attempts": attempts, "originals_unchanged": unchanged,
                  "source_stable": code_before == code_after}, ensure_ascii=False))
