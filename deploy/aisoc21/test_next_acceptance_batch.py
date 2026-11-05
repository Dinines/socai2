"""Offline checks only: no imports of remote identities, SSH, DB or model."""
import ast
import hashlib
import ipaddress
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest

SOURCE = Path(__file__).with_name("next_acceptance_remote.py")


def functions():
    tree = ast.parse(SOURCE.read_text("utf-8"))
    names = {"uid", "fixture", "stages", "case_first", "alert_ids", "seed", "reuse", "export_clause", "phase_allowed",
        "accepted_first_result", "human_and_second"}
    code = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
    ns = {"BATCH": "r1", "datetime": datetime, "UTC": UTC, "timedelta": timedelta, "NAMESPACE_URL": NAMESPACE_URL,
        "UUID": UUID, "uuid5": uuid5, "json": json, "hashlib": hashlib, "ipaddress": ipaddress,
        "service": SimpleNamespace(TENANT=str(uuid4()), DATABASE="socai2_next_20261104")}
    exec(compile(code, str(SOURCE), "exec"), ns)  # noqa: S102 -- trusted repository functions; exclude all remote top-level code
    return ns


def test_batch_keys_are_distinct_and_closed_batch_never_dispatches():
    ns = functions()
    first = {name: ns["uid"](name) for name in ("A0", "A1", "I", "case", "C1", "H", "prepare", "C2")}
    ns["BATCH"] = "r2"
    second = {name: ns["uid"](name) for name in first}
    ns["BATCH"] = "r3"
    third = {name: ns["uid"](name) for name in first}
    ns["BATCH"] = "r4"
    fourth = {name: ns["uid"](name) for name in first}
    ns["BATCH"] = "r5"
    fifth = {name: ns["uid"](name) for name in first}
    ns["BATCH"] = "r6"
    sixth = {name: ns["uid"](name) for name in first}
    ns["BATCH"] = "r7"
    seventh = {name: ns["uid"](name) for name in first}
    assert len(set(first.values()) | set(second.values()) | set(third.values()) | set(fourth.values()) | set(fifth.values()) | set(sixth.values()) | set(seventh.values())) == 56
    for batch in ("r1", "r2", "r3", "r4", "r5", "r6"):
        assert ns["phase_allowed"](batch, "export")
        assert all(not ns["phase_allowed"](batch, phase) for phase in ("seed", "auth", "stages", "first", "second", "reuse"))
    assert ns["phase_allowed"]("r7", "reuse") and not ns["phase_allowed"]("r7", "seed")
    with pytest.raises(AssertionError, match="original batch"):
        ns["seed"]()


def test_r7_routes_use_reused_incident_and_new_case():
    ns = functions()
    original = ns["fixture"]()
    ns["BATCH"] = "r7"
    aids = [str(uuid4()), str(uuid4())]
    saved = {"fixture": original, "reuse": {"alert_ids": aids}}
    calls, starts = [], []
    ns["read"] = saved.__getitem__
    def capture(label, method, path, body):
        calls.append((label, method, path, body))
        return {"case_id": "new-case", "pending_run_id": "new-run", "scope_revision": 1}
    ns["http"], ns["start_round"] = capture, lambda *args: starts.append(args)
    ns["stages"]()
    ns["case_first"]()
    assert calls[2][2] == f"/api/v1/socai2/incidents/{original['incident_id']}/diagnose"
    assert calls[3][3]["incident_ids"] == [original["incident_id"]]
    assert calls[3][3]["operation_key"] == ns["uid"]("case")
    assert starts == [("C1", "new-case", "new-run", 1)]
    assert ns["uid"]("incident") != original["incident_id"]
    assert "source_run_id IN" in ns["export_clause"]("alert_assessments")
    assert "run_id IS NULL" in ns["export_clause"]("artifacts")
    assert "case_id" in ns["export_clause"]("run_steps")


def test_reuse_checks_source_materials_without_copying_old_models(tmp_path):
    ns = functions()
    data = ns["fixture"]()
    aids = [str(uuid4()), str(uuid4())]
    fused = {"seeded": [{"alert_id": aid} for aid in aids]}
    source = tmp_path / "next-acceptance-r1"
    source.mkdir()
    for name, content in [("fixture", data), ("fusion", fused)]:
        (source / (name + ".json")).write_text(json.dumps(content))
    (source / "old-model-response.json").write_text('{"must_not_copy":true}')
    ns["BATCH"], ns["EVIDENCE_ROOT"] = "r7", tmp_path
    saved = {}
    ns["save"] = lambda name, value: saved.setdefault(name, value)
    def pg(database, query):
        assert database == "socai2_next_20261104" and query.startswith("SELECT ")
        index = next(i for i, aid in enumerate(aids) if aid in query)
        return json.dumps({"material_id": str(uuid4()), "raw_json": data["alerts"][index], "incident_id": data["incident_id"]})
    def lake(query):
        assert query.startswith("SELECT ")
        return json.dumps(next(row for row in data["lake_rows"] if row["event_id"] in query))
    ns["service"].pg, ns["service"].lake = pg, lake
    ns["reuse"]()
    assert set(saved) == {"reuse-request", "fixture", "reuse"}
    assert saved["reuse"]["alert_ids"] == aids and saved["fixture"] == data
    assert saved["reuse"]["source_batch"] == "r1" and saved["reuse"]["target_batch"] == "r7"
    assert saved["reuse"]["upstream_writes"] == 0
    assert not saved["reuse"]["prior_requests_and_model_responses_copied"]


def test_wrapper_forwards_batch_only_to_acceptance(tmp_path, monkeypatch):
    import argparse
    import re
    import shlex
    import sys
    source = Path(__file__).with_name("run_next_remote.py")
    tree = ast.parse(source.read_text("utf-8"))
    code = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"], type_ignores=[])
    calls = []
    def capture(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(stdout=b'{}\n', stderr=b'', returncode=0)
    ns = {"argparse": argparse, "re": re, "shlex": shlex, "Path": Path, "ROOT": tmp_path,
        "SSH": ["synthetic-ssh-never-run"], "DEST": "synthetic", "datetime": datetime, "UTC": UTC,
        "subprocess": SimpleNamespace(run=capture), "json": json, "hashlib": hashlib}
    exec(compile(code, str(source), "exec"), ns)  # noqa: S102 -- trusted main with intercepted process runner
    monkeypatch.setattr(sys, "argv", [str(source), "next-20261104-n8", "acceptance", "reuse", "--batch", "r5"])
    assert ns["main"]() == 0
    assert shlex.split(calls[-1][-1])[-3:] == ["reuse", "--batch", "r5"]
    assert len(list(tmp_path.rglob("*-r5-reuse/receipt.json"))) == 1
    monkeypatch.setattr(sys, "argv", [str(source), "next-20261104-n6", "service", "verify"])
    assert ns["main"]() == 0
    assert shlex.split(calls[-1][-1])[-1] == "verify"
    assert "--batch" not in shlex.split(calls[-1][-1])
    monkeypatch.setattr(sys, "argv", [str(source), "next-20261104-n7", "service", "start", "--model-profile", "deepseek"])
    assert ns["main"]() == 0
    assert shlex.split(calls[-1][-1])[-3:] == ["start", "--model-profile", "deepseek"]


def test_second_round_requires_accepted_model_result_before_any_http():
    from copy import deepcopy
    ns = functions()
    run = {"id": "run", "case_id": "case", "state": "completed"}
    result = {"id": "result", "case_id": "case", "source_run_id": "run", "kind": "baseline",
        "conclusion_origin": "model", "validation_state": "accepted", "conclusion": "supported scope-limited result"}
    saved = {"case-create-response": {"body": {"case_id": "case", "scope_revision": 1}}, "fixture": {},
        "C1-response": {"status": 200, "body": {"run": run, "result_ids": ["result"]}},
        "C1-result-0-response": {"status": 200, "body": {"run": run, "result": result}}}
    ns["read"] = saved.__getitem__
    assert ns["accepted_first_result"]("case") == "result"
    bad = []
    for state in ("failed", "unknown", "running"):
        item = deepcopy(saved); item["C1-response"]["body"]["run"]["state"] = state; bad.append(item)
    for state in ("system_only", "not_checked", "rejected", "legacy_unverified", "valid"):
        item = deepcopy(saved); item["C1-result-0-response"]["body"]["result"]["validation_state"] = state; bad.append(item)
    for value in (None, "", " "):
        item = deepcopy(saved); item["C1-result-0-response"]["body"]["result"]["conclusion"] = value; bad.append(item)
    item = deepcopy(saved); item["C1-result-0-response"]["body"]["result"]["conclusion_origin"] = "system"; bad.append(item)
    item = deepcopy(saved); item["C1-result-0-response"]["body"]["result"]["source_run_id"] = "other"; bad.append(item)
    calls = []
    ns["http"] = lambda *args, **kwargs: calls.append(args)
    for item in bad:
        ns["read"] = item.__getitem__
        with pytest.raises(AssertionError):
            ns["human_and_second"]()
    assert not calls  # no H, prepare or model dispatch on a failed prerequisite


def test_deepseek_profile_preserves_original_env_and_only_records_metadata(tmp_path, capsys):
    import io
    source = Path(__file__).with_name("next_service_remote.py")
    tree = ast.parse(source.read_text("utf-8"))
    code = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "configure_deepseek"], type_ignores=[])
    original = b'OPENAI_MODEL=original-alias\nOPENAI_API_KEY=original-synthetic-key\nAISOC_AIRGAP_ALLOWLIST=["local.invalid"]\n'
    (tmp_path/"api.env").write_bytes(original)
    def secure_write(path, value):
        path.write_text(value)
        path.chmod(0o600)
    ns = {"json": json, "sys": SimpleNamespace(stdin=io.StringIO('{"token":"new-synthetic-key"}')),
        "PRIVATE": tmp_path, "candidate": dict, "secure_write": secure_write,
        "protected_model_config": lambda: {"old-config": "fixed"}}
    exec(compile(code, str(source), "exec"), ns)  # noqa: S102 -- trusted function, local-only dependencies
    ns["configure_deepseek"]()
    assert (tmp_path/"api.env").read_bytes() == original
    profile = dict(line.split("=", 1) for line in (tmp_path/"model.deepseek.env").read_text().splitlines())
    assert profile["OPENAI_MODEL"] == "deepseek-flash" and profile["OPENAI_API_KEY"] == "new-synthetic-key"
    assert json.loads(profile["AISOC_AIRGAP_ALLOWLIST"]) == ["api.deepseek.com", "local.invalid"]
    assert "new-synthetic-key" not in capsys.readouterr().out
    ns["sys"].stdin = io.StringIO('{"token":"another-synthetic-key"}')
    with pytest.raises(ValueError, match="already prepared"):
        ns["configure_deepseek"]()
    assert (tmp_path/"api.env").read_bytes() == original
