"""Offline independent review of report-freeze-02. Creates new review evidence only."""
import contextlib
import hashlib
import json
import pathlib
import shutil
import sys
import tempfile
from collections import Counter
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).resolve().parent
FREEZE = HERE / "report-freeze-02"
OUT = HERE / "independent-report-data-01"
COMPLETE = ROOT / "docs/operations/evidence/acceptance-append-20261117-02/prepared"
INCOMPLETE = ROOT / "docs/operations/evidence/acceptance-append-20261117-01/prepared"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


for file in read(FREEZE / "manifest.json")["files"]:
    assert sha(FREEZE / file["path"]) == sha(ROOT / file["path"]) == file["sha256"]
OUT.mkdir()
sys.dont_write_bytecode = True
sys.path[:0] = [str(FREEZE / "tools/testdata"), str(ROOT / "tools/testdata")]
from acceptance_report import report_exit_code, write_session_report
from acceptance_report_models import model_report

before = {"02": inventory(COMPLETE), "01": inventory(INCOMPLETE)}
blocked_access = []
connection_paths = {
    pathlib.Path(path).resolve()
    for prepared in (COMPLETE, INCOMPLETE)
    for path in read(prepared / "session.json")["profile"]["connection_files"].values()
}
original_open = pathlib.Path.open


def guarded_open(path, *args, **kwargs):
    if path.resolve() in connection_paths:
        blocked_access.append("connection_file")
        raise AssertionError("connection files forbidden")
    return original_open(path, *args, **kwargs)


def no_socket(*args, **kwargs):
    blocked_access.append("socket")
    raise AssertionError("network forbidden")


@contextlib.contextmanager
def offline():
    with patch.object(pathlib.Path, "open", guarded_open), patch("socket.socket", no_socket), patch("socket.create_connection", no_socket):
        yield


def validate_files(prepared, output, report):
    manifest = read(output / "manifest.json")
    assert read(output / "report.json") == report
    assert all(sha(output / f["path"]) == f["sha256"] for f in manifest["files"])
    assert all(sha(prepared / f["path"]) == f["sha256"] for f in manifest["sources"])
    for item in report["models"]["requests"]:
        def source(key):
            origin = item[key]
            value = read(prepared / origin["path"])
            for part in origin["pointer"].split("/")[1:]:
                value = value[int(part)] if isinstance(value, list) else value[part]
            return value
        request = source("source")["content_json"]
        body = request.get("payload", request)["body"]
        assert read(output / item["exports"]["messages"]) == [{"role": m["role"], "content": m["content"]} for m in body["messages"]]
        assert read(output / item["exports"]["schema"]) == body["response_format"]
        response = source("response_source")["content_json"]["raw"]
        assert (output / item["exports"]["output"]).read_bytes() == response["choices"][0]["message"]["content"].encode()
    return {"file_count": len(manifest["files"]), "source_count": len(manifest["sources"]), "readback": "passed"}


with offline():
    complete = write_session_report(COMPLETE, OUT / "report-02")
    incomplete = write_session_report(INCOMPLETE, OUT / "report-01")
    exported = validate_files(COMPLETE, OUT / "report-02", complete)
    validate_files(INCOMPLETE, OUT / "report-01", incomplete)

final_path = COMPLETE.parent / "final-records.json"
final = read(final_path)
artifacts = {a["id"]: a for a in final["artifacts"]}
expected_counts = {table: len({r["id"] for r in final[table]}) for table in complete["counts"]}
assert complete["counts"] == expected_counts
assert complete["counts"]["runs"] == 8 and complete["counts"]["results"] == 4
assert [p["newly_observed"]["runs"] for p in complete["parts"]] == [4, 4]
assert complete["models"]["request_count"] == 13
raw_responses = [a for a in artifacts.values() if isinstance(a.get("content_json"), dict)
                 and a["content_json"].get("request_artifact_id") in {
                     a["id"] for a in artifacts.values() if a["kind"] == "model_request"}
                 and isinstance(a["content_json"].get("raw"), dict)]
totals = {key: sum(a["content_json"]["raw"]["usage"][key] for a in raw_responses)
          for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
assert complete["models"]["usage"] == totals
assert totals["total_tokens"] == 109995
assert complete["models"]["finish_reasons"] == {"stop": 13}

expected_quality = []
for artifact in artifacts.values():
    content = artifact.get("content_json") or {}
    if artifact["kind"] != "source_snapshot" or not isinstance(content, dict):
        continue
    schema = content.get("schema_version")
    reviews = ["citation_review", "validation_review"] if schema == "socai2.baseline-delivery.v2" else ["quality"] if schema == "socai2.stage-delivery.v1" else []
    for review in reviews:
        for issue in content.get(review, {}).get("issues", []):
            expected_quality.append({"artifact_id": artifact["id"], "run_id": artifact["run_id"],
                "stage": "C6" if schema == "socai2.baseline-delivery.v2" else content["stage"],
                "review": review, "code": issue["code"], "path": issue.get("path")})
project = lambda x: tuple(x[k] for k in ("artifact_id", "run_id", "stage", "review", "code", "path"))
assert {project(x) for x in complete["quality"]["issues"]} == {project(x) for x in expected_quality}
assert Counter(x["stage"] for x in expected_quality) == {"C6": 9, "C3": 6, "I": 2}
assert len(complete["step_issues"]) == 16

incident_scopes = []
for subject in complete["subjects"]:
    if subject["kind"] != "incident":
        continue
    for reported in subject["rounds"]:
        run = next(r for r in final["runs"] if r["id"] == reported["run_id"])
        source = artifacts[run["input_artifact_id"]]
        selected = source["content_json"]["input_selection"]
        incident_scopes.append({"run_id": run["id"], "input_artifact_id": source["id"],
            "actual_selected_alert_ids": selected["selected_alert_ids"],
            "actual_selected_count": selected["selected_count"],
            "reported_frozen_alert_ids": reported["frozen_alert_ids"]})

assert incomplete["statistics_state"] == "incomplete"
assert all(v is None for v in incomplete["counts"].values())
assert incomplete["parts"][0]["error_code"] == "http_status_503"
assert incomplete["models"]["request_count"] is None
assert not any("stopped-batch" in s["path"] for s in incomplete["sources"])

with tempfile.TemporaryDirectory(prefix="socai2-report-independent-") as temporary:
    prepared = pathlib.Path(temporary) / "prepared"
    shutil.copytree(COMPLETE, prepared)
    part2 = prepared / "runs/part2"
    stash = pathlib.Path(temporary) / "part2"
    part2.rename(stash)
    with offline():
        prefix = write_session_report(prepared, OUT / "prefix-report")
    assert prefix["state"] == "waiting_append" and prefix["next_part"] == "part2"
    assert prefix["counts"]["runs"] == 4 and prefix["counts"]["results"] == 2
    assert prefix["models"]["request_count"] == 6
    stash.rename(part2)
    snapshot = part2 / "saved-records.json"
    data = read(snapshot)
    first_ids = {a["id"] for a in read(prepared / "runs/part1/saved-records.json")["artifacts"]}
    index, request = next((i, a) for i, a in enumerate(data["artifacts"])
                          if a["kind"] == "model_request" and a["id"] not in first_ids)
    body = request["content_json"].get("payload", request["content_json"])["body"]
    patch_info = {"source": "runs/part2/saved-records.json", "original_sha256": sha(snapshot),
        "artifact_id": request["id"], "artifact_index": index,
        "operation": "set first message role to object", "value": {"invalid": "PRIVATE_SENTINEL"}}
    body["messages"][0]["role"] = patch_info["value"]
    snapshot.write_text(json.dumps(data, ensure_ascii=False))
    patch_info["derived_sha256"] = sha(snapshot)
    try:
        with offline():
            malformed = write_session_report(prepared, OUT / "malformed-report")
        bad_nested = {"raised": False, "report_issues": malformed["report_issues"], "model_issues": malformed["models"]["issues"]}
    except Exception as exc:
        bad_nested = {"raised": True, "exception_type": type(exc).__name__,
                      "report_saved": (OUT / "malformed-report/report.json").exists()}
    write(OUT / "malformed-message-patch.json", patch_info)

synthetic = {"request": {"id": "request", "kind": "model_request", "content_json": {"body": {
    "messages": [{"role": "user", "content": " visible \n", "reasoning_content": "HIDDEN_SENTINEL"}],
    "headers": {"Authorization": "AUTH_SENTINEL"}, "response_format": {"type": "json_object"}}}},
    "response": {"id": "response", "kind": "source_snapshot", "content_json": {"request_artifact_id": "request", "raw": {
        "choices": [{"message": {"content": " \n ", "reasoning_content": "HIDDEN_SENTINEL"}, "finish_reason": "stop"}]}}}}
with offline():
    usage, files = model_report(synthetic, {k: {"path": "controlled", "pointer": "/" + k, "sha256": "controlled"} for k in synthetic}, True)
assert usage["usage"]["total_tokens"] is None and usage["unknown_usage_requests"]["total_tokens"] == 1
assert files["models/request/output.txt"] == b" \n "
assert not any(b"SENTINEL" in v for v in files.values())

after = {"02": inventory(COMPLETE), "01": inventory(INCOMPLETE)}
assert before == after and not blocked_access
for file in read(FREEZE / "manifest.json")["files"]:
    assert sha(FREEZE / file["path"]) == sha(ROOT / file["path"]) == file["sha256"]
write(OUT / "source-hashes.json", before)
write(OUT / "quality-source-details.json", expected_quality)
summary = {"freeze": "report-freeze-02/manifest.json", "source_files_unchanged": {k: len(v) for k, v in before.items()},
    "offline_forbidden_access_attempts": blocked_access, "new_business_actions": 0, "new_model_calls": 0,
    "actual_counts": expected_counts, "model_usage": totals, "quality_counts": dict(Counter(x["stage"] for x in expected_quality)),
    "step_issues": 16, "exports": exported, "prefix": {"runs": 4, "results": 2, "requests": 6, "next_part": "part2"},
    "failed_01": {"statistics": "incomplete", "error_code": "http_status_503", "outside_fallback": False},
    "incident_scope_mismatch": incident_scopes, "malformed_message": bad_nested,
    "attempt_outcomes_exported": "\"outcome\"" in json.dumps(complete),
    "controlled_missing_usage_privacy_whitespace": "passed"}
write(OUT / "results.json", summary)
print(json.dumps(summary, ensure_ascii=False, indent=2))
