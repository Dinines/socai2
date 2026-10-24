"""Probe-file reconciliation only: no network, database or model execution."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("verify_tool_handoff", Path(__file__).parents[1] / "verify_tool_handoff.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

IDENTITY = {"tenant_id": "11111111-1111-4111-8111-111111111111",
            "run_id": "22222222-2222-4222-8222-222222222222",
            "canonical_alert_id": "33333333-3333-4333-8333-333333333333"}


def put(root, kind, index, **data):
    (root / f"{kind}-{index:02}.json").write_text(json.dumps({"index": index, **data}))


def make_call(call_id="call-1", tool="authentication_events", args=None):
    return {"id": call_id, "type": "function", "function": {"name": tool,
            "arguments": json.dumps(args or {"user_name": "u-secret", "hours": 24})}}


def fixture(root, calls=None, result=None, later=True):
    calls = calls or [make_call()]
    result = result if result is not None else {"available": False, "reason": "private-reason"}
    put(root, "model-request", 1, alert=IDENTITY, body={"messages": []})
    put(root, "model-response", 1, status_code=200,
        body={"choices": [{"message": {"role": "assistant", "tool_calls": calls}}]})
    messages = [{"role": "assistant", "tool_calls": calls}]
    for index, call in enumerate(calls, 1):
        execution = {"alert": IDENTITY, "tool": call["function"]["name"],
                     "args": json.loads(call["function"]["arguments"])}
        put(root, "tool-request", index, **execution)
        put(root, "tool-result", index, **execution, result=result, model_tool_content=v.renderer()(result))
        messages.append({"role": "tool", "tool_call_id": call["id"], "content": v.renderer()(result)})
    if later:
        put(root, "model-request", 2, alert=IDENTITY, body={"messages": messages})


def edit(root, name, change):
    path = root / name
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))


def test_failed_lookup_can_be_present_in_actual_next_model_request_without_leaking_text(tmp_path):
    fixture(tmp_path)
    report = v.verify(tmp_path)
    assert report["counts"]["return_status"] == {"unavailable": 1}
    assert report["counts"]["handoff"] == {"verified_in_later_request": 1}
    assert "private-reason" not in json.dumps(report)
    assert "u-secret" not in json.dumps(report)


@pytest.mark.parametrize("field", ["run_id", "tenant_id", "canonical_alert_id"])
def test_later_request_must_belong_to_same_run_tenant_and_alert(tmp_path, field):
    fixture(tmp_path)
    edit(tmp_path, "model-request-02.json", lambda data: data["alert"].update({field: "44444444-4444-4444-8444-444444444444"}))
    assert v.verify(tmp_path)["records"][0]["handoff"] == "not_in_later_request"


def test_same_arguments_repeated_have_distinct_ordered_one_to_one_call_ids(tmp_path):
    fixture(tmp_path, calls=[make_call("first"), make_call("second")])
    report = v.verify(tmp_path)
    assert [row["call_id"] for row in report["records"]] == ["first", "second"]
    assert report["counts"]["handoff"] == {"verified_in_later_request": 2}


def test_missing_repeated_occurrence_is_unverified_not_guessed(tmp_path):
    fixture(tmp_path, calls=[make_call("first"), make_call("second")])
    (tmp_path / "tool-request-01.json").unlink()
    (tmp_path / "tool-result-01.json").unlink()
    report = v.verify(tmp_path)
    assert report["records"][0]["pairing"] == "unverified"
    assert report["counts"]["unpaired_model_calls"] == 2


def test_last_tool_without_actual_later_request_remains_unconsumed(tmp_path):
    fixture(tmp_path, later=False)
    assert v.verify(tmp_path)["records"][0]["handoff"] == "not_in_later_request"


def test_tampered_return_cannot_match_recorded_render(tmp_path):
    fixture(tmp_path)
    edit(tmp_path, "tool-result-01.json", lambda data: data["result"].update(available=True))
    row = v.verify(tmp_path)["records"][0]
    assert row["render_consistency"] == "mismatch"
    assert row["return_status"] == "unverified"
    assert row["handoff"] == "unverified"


def test_tampered_model_tool_message_is_not_accepted(tmp_path):
    fixture(tmp_path)
    edit(tmp_path, "model-request-02.json", lambda data: data["body"]["messages"][-1].update(content="changed"))
    assert v.verify(tmp_path)["records"][0]["handoff"] == "content_mismatch"


@pytest.mark.parametrize("result,status", [({"available": True, "rows": []}, "available"),
                                         ({"error": "private-error"}, "error"),
                                         ({"rows": []}, "returned_unclassified")])
def test_return_states_do_not_infer_relevant_evidence(tmp_path, result, status):
    fixture(tmp_path, result=result)
    assert v.verify(tmp_path)["records"][0]["return_status"] == status


def test_result_from_another_run_cannot_be_used(tmp_path):
    fixture(tmp_path)
    edit(tmp_path, "tool-result-01.json", lambda data: data["alert"].update(run_id="44444444-4444-4444-8444-444444444444"))
    row = v.verify(tmp_path)["records"][0]
    assert (row["return_status"], row["handoff"]) == ("unverified", "unverified")


def test_duplicate_call_id_and_conflicting_execution_order_are_unverified(tmp_path):
    fixture(tmp_path, calls=[make_call("same"), make_call("same")])
    assert all(row["pairing"] == "unverified" for row in v.verify(tmp_path)["records"])
    fixture(tmp_path, calls=[make_call("first"), make_call("second", args={"user_name": "other"})])
    for kind in ("tool-request", "tool-result"):
        one = json.loads((tmp_path / f"{kind}-01.json").read_text())
        two = json.loads((tmp_path / f"{kind}-02.json").read_text())
        one.pop("index"); two.pop("index")
        put(tmp_path, kind, 1, **two); put(tmp_path, kind, 2, **one)
    assert all(row["pairing"] == "unverified" for row in v.verify(tmp_path)["records"])


def test_missing_return_and_orphan_are_kept_separate(tmp_path):
    fixture(tmp_path)
    (tmp_path / "tool-result-01.json").rename(tmp_path / "tool-result-02.json")
    edit(tmp_path, "tool-result-02.json", lambda data: data.update(index=2))
    report = v.verify(tmp_path)
    assert report["records"][0]["return_status"] == "missing_return"
    assert report["counts"]["orphan_returns"] == 1


def test_file_indexes_and_identity_are_required(tmp_path):
    fixture(tmp_path)
    edit(tmp_path, "model-request-01.json", lambda data: data.update(index=9))
    with pytest.raises(ValueError, match="index"):
        v.verify(tmp_path)


def test_report_is_private_exclusive_and_only_under_local(tmp_path, monkeypatch):
    monkeypatch.setattr(v, "LOCAL_ROOT", tmp_path / ".local")
    report = {"status": "offline"}
    out = tmp_path / ".local/report.json"
    v.save_report(out, report)
    assert out.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        v.save_report(out, report)
    with pytest.raises(ValueError, match=".local"):
        v.save_report(tmp_path / "report.json", report)
    (tmp_path / ".local/escape").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match=".local"):
        v.save_report(tmp_path / ".local/escape/report.json", report)
