"""Saved 21 rounds become exact display links, without opening connections."""
import json
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/testdata"))
from acceptance import main
from acceptance_console import run_console
from acceptance_materials import MaterialError
from acceptance_report import write_session_report
from acceptance_report_links import ReportConfig, add_workbench_links
from alert_scenarios import sha256

PREPARED = ROOT / "docs/operations/evidence/acceptance-fullflow-21-20261117-01/results/prepared"
CONFIG = {"schema_version": "socai2.acceptance-report-config.v1",
          "source_environment_label": "21 正式调查服务（aisoc.socai2）",
          "workbench_environment_label": "acceptance-release-20261117-01",
          "workbench_url": "http://127.0.0.1:4177/viewer/"}


def test_report_cli_links_saved_rounds_without_changing_originals(tmp_path, capsys):
    before = {str(p): sha256(p.read_bytes()) for p in PREPARED.rglob("*") if p.is_file()}
    config = tmp_path / "report-config.json"
    config.write_text(json.dumps(CONFIG))
    output = tmp_path / "report"
    with patch("socket.socket", side_effect=AssertionError("report must remain offline")):
        assert main(["report", "--prepared", str(PREPARED), "--output", str(output),
                     "--report-config", str(config)]) == 0
    capsys.readouterr()
    report = json.loads((output / "report.json").read_text())
    markdown = (output / "report.md").read_text()
    links = []
    for subject in report["subjects"]:
        for run in subject["rounds"]:
            link = run["viewer_url"]
            query = parse_qs(urlsplit(link).query)
            assert query == {"subject_type": [subject["kind"]], "subject_id": [subject["id"]],
                             "run_id": [run["run_id"]], "environment": [CONFIG["workbench_environment_label"]]}
            assert f"[在工作台打开第 {run['round']} 轮]({link})" in markdown
            links.append(link)
    assert len(links) == len(set(links)) == 6
    case = next(s for s in report["subjects"] if s["kind"] == "case")
    assert [r["run_id"] for r in case["rounds"]] == ["c068a7b9-b33d-45a5-b0c0-c2b296ba5d5d", "57683158-b770-4697-8ca3-a2707ed0af1b"]
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["workbench"] == report["workbench"] == {"configured": True, **CONFIG}
    assert all(sha256((output / f["path"]).read_bytes()) == f["sha256"] for f in manifest["files"])
    assert before == {str(p): sha256(p.read_bytes()) for p in PREPARED.rglob("*") if p.is_file()}


def test_environment_mismatch_rejected_before_creating_report(tmp_path):
    config = ReportConfig.model_validate({**CONFIG, "source_environment_label": "other environment"})
    with patch("socket.socket", side_effect=AssertionError("offline")), pytest.raises(MaterialError, match="environment"):
        write_session_report(PREPARED, tmp_path / "wrong", report_config=config)
    assert not (tmp_path / "wrong").exists()


def test_console_report_uses_the_same_public_configuration(tmp_path):
    answers = iter(["report", "quit"])
    with patch("socket.socket", side_effect=AssertionError("offline")):
        assert run_console(PREPARED, tmp_path / "console", report_config=ReportConfig.model_validate(CONFIG),
                           read=lambda _: next(answers), write=lambda _: None,
                           execute=lambda *_: pytest.fail("must not execute")) == 0
    report = json.loads((tmp_path / "console/reports/0001/report.json").read_text())
    assert report["workbench"]["configured"]
    assert sum(bool(r.get("viewer_url")) for s in report["subjects"] for r in s["rounds"]) == 6


@pytest.mark.parametrize("url", ["file:///viewer/", "https://user:secret@host/viewer/", "http://host/viewer/?run_id=x"])
def test_report_configuration_accepts_only_plain_http_page_addresses(url):
    with pytest.raises(ValueError):
        ReportConfig.model_validate({**CONFIG, "workbench_url": url})


def test_ipv6_authority_remains_a_valid_browser_address():
    value = {"environment": {"label": CONFIG["source_environment_label"]}, "subjects": [{"kind": "case",
        "id": "8bf67e9e-a46a-58ba-a3ad-73a70ca64258", "rounds": [{"run_id": "c068a7b9-b33d-45a5-b0c0-c2b296ba5d5d"}]}]}
    add_workbench_links(value, ReportConfig.model_validate({**CONFIG, "workbench_url": "http://[::1]:4177/viewer/"}))
    address = urlsplit(value["subjects"][0]["rounds"][0]["viewer_url"])
    assert address.hostname == "::1" and address.port == 4177 and address.path == "/viewer/"
