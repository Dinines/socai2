"""Sequential cases through the deployed HTTP caller; save every request/response."""
import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import NAMESPACE_URL, uuid5


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class CaseRun:
    def __init__(self, args, case, token):
        self.args, self.case, self.token = args, case, token
        self.directory = args.output / case["id"]
        self.directory.mkdir()
        self.summary = {"id": case["id"], "input": case, "checks": [], "requests": [], "runs": []}
        self.number = 0

    def checkpoint(self):
        save(self.directory / "summary.json", self.summary)

    def check(self, condition, label):
        self.summary["checks"].append({"check": label, "passed": bool(condition)})
        self.checkpoint()

    def key(self, action):
        return str(uuid5(NAMESPACE_URL, f"{self.args.batch}:{self.case['id']}:{action}"))

    def request(self, method, label, path, body=None, expected=(200,)):
        self.number += 1
        stem = self.directory / f"{self.number:03}-{label}"
        entry = {"method": method, "path": path, "body": body, "started_at": datetime.now(UTC).isoformat(),
                 "response_file": stem.name + ".response.txt", "state": "pending"}
        save(stem.with_suffix(".request.json"), entry)
        self.summary["requests"].append(entry)
        self.checkpoint()
        print(json.dumps({"case": self.case["id"], "step": label, "state": "begin"}), flush=True)
        command = [sys.executable, "-B", str(self.args.client), method, path,
                   "--base-url", self.args.base_url, "--core-base-url", self.args.core_base_url, "--timeout", "180"]
        if body is not None:
            body_path = stem.with_suffix(".body.json")
            save(body_path, body)
            command += ["--body", str(body_path)]
        try:
            result = subprocess.run(command, env={**os.environ, "AISOC_API_TOKEN": self.token}, capture_output=True, timeout=190)
            raw = result.stdout[:-1] if result.stdout.endswith(b"\n") else result.stdout
            stem.with_suffix(".response.txt").write_bytes(raw)
            found = re.search(r"HTTP (\d+)", result.stderr.decode("utf-8", errors="replace"))
            entry.update(state="returned" if found else "unknown", status=int(found[1]) if found else None,
                         response_sha256=hashlib.sha256(raw).hexdigest(), client_exit=result.returncode)
            self.checkpoint()
            assert entry["status"] in expected, f"{label}: HTTP {entry['status']}, client exit {result.returncode}; no retry"
            try:
                return json.loads(raw)
            except ValueError:
                return raw.decode("utf-8")
        except BaseException:
            self.checkpoint()
            raise

    def inspect_run(self, run, label):
        data, case = run["result"], self.case
        self.summary["runs"].append({"label": label, "run_id": run["run_id"], "status": run["status"],
            "stop_reason": data["stop_reason"], "completion": data["completion"], "usage": data["usage"],
            "scope": run["scope"], "member_coverage": data["report"].get("member_coverage")})
        reread = self.request("GET", label + "-result", run["result_url"])
        self.check(reread["result"] == data, label + ": result readback identical")
        report = self.request("GET", label + "-report", run["report_url"])
        self.check(report == data["markdown"], label + ": downloaded report identical")
        steps = self.request("GET", label + "-steps", run["steps_url"] + "?limit=50")["items"]
        for step in steps:
            self.request("GET", label + f"-step-{step['seq']}", step["detail_url"])
        evidence = self.request("GET", label + "-evidence-list", run["evidence_url"])["items"]
        for item in evidence:
            detail = self.request("GET", label + "-evidence-" + item["evidence_id"], item["detail_url"])
            if detail["rows"]:
                row = self.request("GET", label + "-row-" + item["evidence_id"], detail["rows"][0]["url"])
                self.check(row["row"] == detail["evidence"]["rows"][0], label + ": source row " + item["evidence_id"])
            if item["kind"] == "tool":
                self.check(bool(detail["tool_trace"] and detail["tool_trace"]["request_step_url"] and detail["tool_trace"]["response_step_url"]), label + ": Tool exchange links " + item["evidence_id"])
        for kind, identity in [("alert", case["alert_ids"][0]), ("incident", case["incident_id"]), ("case", run["case_id"])]:
            page = self.request("GET", label + "-index-" + kind, f"/api/v2/investigation/executions?{kind}_id={identity}&limit=50")
            indexed = next((x for x in page["items"] if x["run_id"] == run["run_id"]), None)
            self.check(indexed is not None and indexed["result_url"] == run["result_url"] and indexed["scope"] == run["scope"], label + ": " + kind + " index agrees")
        self.check(run["status"] == "completed", label + ": valid conclusion completed")
        coverage = data["report"].get("member_coverage", {})
        self.check(coverage.get("selected_count") == len(run["scope"]["selected_member_ids"]), label + ": member coverage count")
        self.check(coverage.get("not_assessed_count") == 0, label + ": selected members assessed or unresolved")
        return report

    def overview(self, run):
        result = self.request("POST", "overview-refresh", f"/api/v2/investigation/incidents/{self.case['incident_id']}/overview/refresh?include_investigations=true")
        metadata = result["ai_overview_metadata"]
        self.check(metadata["last_attempt_status"] == "succeeded" and metadata["status"] == "ready", "overview: generated and saved")
        self.check(run["run_id"] in (metadata.get("source_refs") or {}).get("investigation_run_ids", []), "overview: new Run cited")
        reread = self.request("GET", "overview-readback", f"/api/v2/investigation/incidents/{self.case['incident_id']}")
        self.check(reread["ai_overview"] == result["ai_overview"] and reread["ai_overview_metadata"] == metadata, "overview: GET preserves text and source metadata")
        self.summary["overview_usage"] = metadata.get("last_usage")
        return result

    def execute(self):
        case, root = self.case, "/api/v2/investigation"
        initial = [self.request("GET", f"source-{i}", f"/api/v1/alerts/{identity}") for i, identity in enumerate(case["alert_ids"])]
        self.request("GET", "incident-before", f"{root}/incidents/{case['incident_id']}")
        for i, identity in enumerate(case["alert_ids"]):
            self.request("GET", f"alert-context-{i}", f"{root}/alerts/{identity}/investigation-context")
        source = {"type": case.get("source_type", "incident"), "alert_ids": case["alert_ids"][:1] if case.get("create_then_attach") else case["alert_ids"]}
        if source["type"] == "incident": source["incident_id"] = case["incident_id"]
        body = {"operation_key": self.key("create"), "source": source,
                "target": {"mode": "create", "title": f"{self.args.batch} {case['id']}"}}
        receipt = self.request("POST", "create-case", root + "/case-links", body, (201,))
        self.summary["case_id"] = receipt["case_id"]
        self.check(self.request("POST", "create-repeat", root + "/case-links", body) == receipt, "create: same key returns receipt")
        if case.get("create_then_attach"):
            attach = {"operation_key": self.key("attach"), "source": {"type": "alerts", "alert_ids": case["alert_ids"]}, "target": {"mode": "attach", "case_id": receipt["case_id"]}}
            linked = self.request("POST", "attach-members", root + "/case-links", attach, (201,))
            self.check(set(linked["added_member_ids"]) == set(case["alert_ids"][1:]) and set(linked["already_linked_member_ids"]) == set(case["alert_ids"][:1]), "attach: added versus existing")
        self.request("GET", "case-core-link", receipt["case_url"])
        self.request("GET", "case-links", f"{root}/case-links?incident_id={case['incident_id']}")
        selected = case["alert_ids"][:case.get("selected_count", len(case["alert_ids"]))]
        scope = {"start": case["start"], "end": case["end"], "selected_member_ids": selected,
                 "question": f"请先分别调用process_activity和network_connections，hostname={case['host']}，limit=20，等待实际结果后综合分析选定告警。区分告警主张与查询证据，列出成员判断、关联依据、时间线、缺口和未决问题；无记录不等于安全。"}
        prefix = f"{root}/cases/{receipt['case_id']}"
        preview = self.request("POST", "preview", prefix + "/investigation-context", scope)
        self.check(set(preview["context"]["all_member_ids"]) == set(case["alert_ids"]) and preview["context"]["selected_member_ids"] == selected, "preview: Case members and selection distinct")
        main_body = {**scope, "operation_key": self.key("main")}
        run = self.request("POST", "main", prefix + "/investigate", main_body)
        original = self.inspect_run(run, "main")
        if run["status"] != "completed":
            self.summary["unexecuted"] = {"followup": "main Run did not complete" if case.get("followup") else "not selected for this case",
                                          "overview": "main Run did not complete"}
        tools = [x for x in run["result"]["evidence"] if x["kind"] == "tool"]
        self.summary["tool_results"] = [{k: x.get(k) for k in ["tool", "arguments", "available", "returned_count", "reason", "query_scope", "reused_from"]} for x in tools]
        self.check({x["tool"] for x in tools} == {"process_activity", "network_connections"}, "main: requested native Tools executed")
        self.check(all(x.get("available") is True and x["arguments"]["hostname"] == case["host"] for x in tools), "main: Tools available within host scope")
        network = next((x for x in tools if x["tool"] == "network_connections"), None)
        self.check(network is not None and len(network.get("rows", [])) == case["expected_network_rows"], "main: expected source record count")
        self.check(self.request("POST", "main-repeat", prefix + "/investigate", main_body)["result"] == run["result"], "main: repeated operation reads original result")
        if len(selected) < len(case["alert_ids"]):
            page = self.request("GET", "unselected-index", f"{root}/executions?alert_id={case['alert_ids'][-1]}&limit=50")
            self.check(all(x["run_id"] != run["run_id"] for x in page["items"]), "unselected member not attributed to this Run")
        overview = None
        if run["status"] == "completed" and case.get("overview_before_followup"):
            overview = self.overview(run)
        if run["status"] == "completed" and case.get("followup"):
            question = "沿用H1历史材料说明目前仍缺哪些来源证据，不重复查询，也不引用旧Run的E编号作为本次引用。"
            if case["followup"] == "reuse_network":
                question = "请先再次调用network_connections，使用前次相同参数" + json.dumps(network["arguments"]) + "，然后说明历史材料的限制；沿用原窗口，不要扩展范围。"
            follow_body = {**scope, "question": question, "operation_key": self.key("followup"), "previous_run_id": run["run_id"]}
            if case.get("followup_required_tools"):
                follow_body["required_tools"] = case["followup_required_tools"]
            follow = self.request("POST", "followup", prefix + "/investigate", follow_body)
            self.inspect_run(follow, "followup")
            self.check(follow["previous_run_id"] == run["run_id"] and follow["previous_result_url"] == run["result_url"], "followup: previous Run link")
            h1 = self.request("GET", "history-evidence", follow["evidence_url"] + "/H1")
            self.check(h1["evidence"]["data"]["report"] == run["result"]["report"], "followup: complete historical report retained")
            if case["followup"] == "reuse_network":
                self.check(any(x.get("reused_from", {}).get("run_id") == run["run_id"] for x in follow["result"]["evidence"]), "followup: matching query reused")
            self.check(self.request("GET", "original-report-after-followup", run["report_url"]) == original, "followup: original Markdown unchanged")
            if overview:
                stale = self.request("GET", "overview-after-new-run", f"{root}/incidents/{case['incident_id']}")
                self.check(stale["ai_overview"] == overview["ai_overview"] and stale["ai_overview_metadata"]["is_stale"], "overview: new Run marks old text stale without regeneration")
            run = follow
        if not overview and run["status"] == "completed": self.overview(run)
        self.request("GET", "case-history", prefix + "/investigations")
        self.request("GET", "incident-investigations", f"{root}/incidents/{case['incident_id']}/investigations")
        fields = ("id", "title", "status", "disposition", "source_event_ids", "description")
        for i, identity in enumerate(case["alert_ids"]):
            after = self.request("GET", f"source-after-{i}", f"/api/v1/alerts/{identity}")
            self.check({k: initial[i].get(k) for k in fields} == {k: after.get(k) for k in fields}, "source Alert unchanged: " + identity)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--tokens", type=Path, required=True, help="Private tenant_id-to-token JSON map; never copied to output")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--client", type=Path, required=True)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--base-url", default="http://127.0.0.1:18010")
    parser.add_argument("--core-base-url", default="http://127.0.0.1:18000")
    args = parser.parse_args()
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,64}", args.batch), "invalid_batch_id"
    manifest, tokens = json.loads(args.manifest.read_text(encoding="utf-8-sig")), json.loads(args.tokens.read_text())
    cases = [x for x in manifest["cases"] if not args.case_ids or x["id"] in args.case_ids]
    assert cases and all(x["tenant_id"] in tokens for x in cases)
    args.output.mkdir(parents=True, exist_ok=False)
    result = {"batch": args.batch, "data_origin": manifest["data_origin"], "cases": []}
    for case in cases:
        runner = CaseRun(args, case, tokens[case["tenant_id"]])
        try:
            runner.execute()
        except Exception as exc:
            runner.summary["error"] = {"type": type(exc).__name__, "message": str(exc)}
        runner.summary["passed"] = not runner.summary.get("error") and all(x["passed"] for x in runner.summary["checks"])
        runner.checkpoint()
        result["cases"].append(runner.summary)
        save(args.output / "batch.json", result)
        print(json.dumps({"case": case["id"], "finished": True, "passed": runner.summary["passed"]}), flush=True)
    result["passed"] = all(x["passed"] for x in result["cases"])
    save(args.output / "batch.json", result)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
