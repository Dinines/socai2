"""Final bounded independent review of saved 4b deployment evidence; no network."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
OWNER = ROOT / "docs/operations/evidence/workbench-4b-release-20261117-01"
BASE = ROOT / "docs/operations/evidence/acceptance-fullflow-21-20261117-01"
PACK = ROOT / ".local/investigation-test-release/test-service-0.6.1-20261117-4b01"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def receipt(name):
    item = read(OWNER / name)
    assert item["exit"] == 0 and not item["stderr"]
    return json.loads(item["stdout"])


prior_names = ["independent-package-review-01.json", "build-host-addendum-01.json",
               "independent-runtime-review-01.json", "independent-report-browser-review-01.json"]
assert all(read(OUT / name)["status"].startswith("passed") for name in prior_names)
report = read(OWNER / "report-02/report.json")
live = read(OWNER / "live-http-verification.json")
pres = read(OWNER / "final-preservation.json")
assert pres == receipt("final-preservation-receipt.json")
pre, deployed, loaded = receipt("preflight-02.json"), receipt("deployment-01.json"), receipt("load-image-01.json")
snap = read(BASE / "results/prepared/runs/part2/saved-records.json")
saved_runs = {r["id"]: r for r in snap["runs"]}
saved_artifacts = {r["id"]: r for r in snap["artifacts"]}
http, checks = {}, []
assert live["status"] == "passed" and live["http_gets"] == len(live["reads"]) == 26
for row in live["reads"]:
    assert row["status"] == 200 and sha(OWNER / row["file"]) == row["sha256"]
    assert row["path"] not in http
    http[row["path"]] = read(OWNER / row["file"])
caps, viewer = http["/test-api/v1/capabilities"], http["/viewer/config.json"]
assert caps["service_version"] == caps["viewer_version"] == "0.6.1"
assert caps["environment_label"] == caps["investigation_http"]["environment_label"] == "acceptance-release-20261117-01"
assert viewer["test_source_prefixes"] == ["lyc", "telemetry-channel-02"]
run_checks = []
for subject in report["subjects"]:
    kind = subject["kind"]
    for row in subject["rounds"]:
        path = "/api/v1/socai2/" + {"case": "cases", "incident": "incidents", "alert": "alerts"}[kind] + "/" + subject["id"]
        path += ("/runs/" if kind == "case" else "/analysis/runs/") + row["run_id"]
        detail = http[path]
        actual = detail["run"] if kind == "case" else http[path + "/trace"]["run"]
        saved = saved_runs[row["run_id"]]
        assert detail["run"]["id"] == actual["id"] == row["run_id"] and actual[kind + "_id"] == subject["id"]
        for key in ["state", "input_artifact_id", "kind"]:
            assert actual[key] == saved[key]
        if kind == "case":
            assert actual["delivery_state"] == saved["delivery_state"] == row["delivery_state"]
            assert detail["input_member_count"] == row["scope"]["selected_count"]
            if row["round"] == 2:
                assert actual["comparison_context"]["previous_run_id"] == row["previous_run_ids"][0]
                assert actual["comparison_context"]["comparison_result_id"] == row["comparison_result_id"]
        run_checks.append({"subject_type": kind, "subject_id": subject["id"], "run_id": actual["id"], "state": actual["state"]})
assert run_checks == live["runs"] and len(run_checks) == 6
checks.append({"id": "F1", "status": "passed", "name": "实际HTTP/Run身份", "detail": "26 GET原始正文SHA全部匹配；6 Run投影/trace归属、输入工件、状态和Case比较身份与原记录一致", "runs": run_checks})

artifacts, contexts, models, copies = [], [], [], []
for path, body in http.items():
    if "/artifacts/" not in path:
        continue
    # The existing HTTP contract uses artifact for Case and metadata for A/I.
    meta = body.get("artifact") or body["metadata"]
    saved = saved_artifacts[meta["id"]]
    assert body["availability"] == "available"
    for key in ["id", "run_id", "case_id", "incident_id", "alert_id", "kind", "schema_version", "sha256", "material_state", "size_bytes"]:
        assert meta[key] == saved[key], (meta["id"], key)
    assert body["content_json"] == saved["content_json"] and body["content_text"] == saved["content_text"]
    artifacts.append({"artifact_id": meta["id"], "run_id": meta["run_id"], "sha256": meta["sha256"]})
    content = body["content_json"]
    if "raw" in content:
        target = models if saved["kind"] == "model_response" or saved["schema_version"] in ["socai2.baseline-analysis.v3", "socai2.baseline-delivery.v2"] else copies
        target.append(meta["id"])
    else:
        assert saved["schema_version"] == "socai2.baseline-context.v1"
        case = next(s for s in report["subjects"] if s["kind"] == "case")
        row = next(r for r in case["rounds"] if r["run_id"] == meta["run_id"])
        ids = content["scope"]["alert_ids"]
        assert sorted(ids) == sorted(row["frozen_alert_ids"])
        sources = [content["alerts"][identity]["alert"]["connector_type"] for identity in ids]
        assert sources == ["telemetry-channel-02"] * row["round"]
        contexts.append({"run_id": meta["run_id"], "frozen_alert_count": len(ids), "sources": sources})
assert len(artifacts) == 14 and len(models) == 8 and len(copies) == 4
assert sorted(c["frozen_alert_count"] for c in contexts) == [1, 2]
assert set(models) == {r["artifact_id"] for r in live["model_originals"]}
assert set(copies) == {r["artifact_id"] for r in live["frozen_upstream_copies"]}
checks.append({"id": "F2", "status": "passed", "name": "当前原答及冻结材料", "detail": "8原答、4上游副本、2个C1的元数据与正文逐值保持；副本不重复计模型调用", "contexts": contexts, "artifacts": artifacts})

manifest = read(PACK / "package-manifest.json")
assert all(sha(PACK / name) == value["sha256"] for name, value in manifest["files"].items())
assert sha(PACK / "package-manifest.json") == loaded["package_manifest_sha256"]
assert pres["container"] == deployed["container"] and pres["container"]["running"]
assert pres["container"]["image"] == loaded["images"]["viewer"]["id"]
assert caps["investigation_http"]["contract_sha256"] == deployed["config_sha256"]["investigation-openapi.json"]
checks.append({"id": "F3", "status": "passed", "name": "发布身份持续一致", "detail": "冻结119文件/manifest保持；最终r8容器与部署回执逐值一致，实际0.6.1/合同正确；两镜像内容沿已验119文件回执", "images": loaded["images"], "container_id": pres["container"]["id"], "build_host": "viewer在21；acceptance本机同配方缓存构建后原样加载21，远端旧失败保留"})
for name, current in pres["core"].items():
    assert current["running"]
    for key in current:
        assert current[key] == pre["core"][name][key], (name, key)
assert pres["ledger_sha256"] == pre["ledger_sha256"] == deployed["ledger_sha256"] and len(pres["ledger_sha256"]) == 8
assert pres["old_viewer_stopped_and_preserved"]
pres_input = read(OWNER / "preservation-input.json")
assert {k: v for k, v in pres_input.items() if k != "prepared_files"} == pre
originals = read(BASE / "results-copy.json")["sha256"]
expected_prepared = {p[len("results/prepared/"):]: h for p, h in originals.items() if p.startswith("results/prepared/")}
assert len(originals) == 1036 and len(expected_prepared) == len(pres_input["prepared_files"]) == pres["prepared_file_count"] == 982
assert expected_prepared == pres_input["prepared_files"] and pres["prepared_files_unchanged"]
assert all(sha(BASE / path) == digest for path, digest in originals.items())
checks.append({"id": "F4", "status": "passed", "name": "范围内服务及数据保持", "detail": "4核心容器完整保留字段和8账本SHA不变，旧r7停机保留；远端982 prepared清单逐项等于原1036母本内prepared子集，本机1036全部重算一致", "core_containers": 4, "ledger_files": 8, "prepared_files": 982, "original_evidence_files": 1036, "count_note": "982为prepared子集；1036包含此前报告等全部原样取回results文件，两数不相加"})
lock = PACK / "deploy/investigation-test/acceptance-requirements.lock"
pins = dict(re.findall(r"^([A-Za-z0-9_-]+)==([^ \n]+)", lock.read_text(), re.M))
assert len(pins) == 19 and pres["dependency_runtime"]["locked_versions"] == pins
assert pres["dependency_runtime"]["python"] == "3.11.17" and pres["dependency_runtime"]["pip_check"] == "No broken requirements found."
checks.append({"id": "F5", "status": "passed", "name": "镜像实际依赖", "detail": "21验收镜像禁网运行读取Python3.11.17/19依赖，与冻结锁定文件相同；pip check通过", "lock_sha256": sha(lock)})

report_review = read(OUT / "independent-report-browser-review-01.json")
for item in report_review["evidence"]:
    assert sha(ROOT / item["path"]) == item["sha256"], item["path"]
for item in report_review["report_checks"]["local_links"]:
    assert sha(ROOT / item["target"]) == item["sha256"]
assert report_review["findings"][0]["status"] == "closed_fixed_and_independently_retested"
checks.append({"id": "F6", "status": "passed", "name": "最终报告与浏览器交付", "detail": "承接且核证据未改：report02的32本地链接/6精确Run链接/24模型导出正确；实际4177两轮冻结1/2紫色、刷新/完成重载、比较及错误目标不latest通过；路径问题关闭", "browser_method": "协调方实际操作，独立审核保存AX/URL/截图及回执；中间加载态保留但不计通过"})
cleanup = read(OWNER / "preview-cleanup.json")
assert cleanup["status"] == "passed" and set(cleanup["closed_ports"]) == {58482, 58483}
assert cleanup["files_deleted"] == 0 and cleanup["active_entry"] == "http://127.0.0.1:4177/viewer/"
checks.append({"id": "F7", "status": "passed", "name": "临时预览收尾", "detail": "协调方回执核58482/58483关闭且文件保留；现用入口4177，审计未重复停止进程"})
assert live["business_posts"] == live["model_calls"] == pres["business_posts"] == pres["model_calls"] == 0
refs = [OUT / name for name in prior_names] + [OWNER / name for name in ["live-http-verification.json", "verify-live-http.py", "live-http-driver-01.json", "live-http-driver-02.json", "final-preservation.json", "final-preservation-receipt.json", "preservation-input.json", "verify-preservation.py", "preview-cleanup.json"]]
refs += [OWNER / row["file"] for row in live["reads"]] + [Path(__file__)]
result = {
    "status": "passed_limited_4b_release_acceptance", "observed_at": datetime.now(timezone.utc).isoformat(),
    "scope": "仅§12.17本次4b测试工具/验收镜像/4177发布及实际读回，不是整个change验收",
    "reviewer_role": "独立测试模块，未参与产品实现或部署；核冻结文件、实际回执、HTTP正文及浏览器证据",
    "release": "workbench-4b-20261117-01", "version": "0.6.1", "workbench_container": "socai2-investigation-test-4177-r8", "checks": checks,
    "findings": [{"id": "REL-report-path", "severity": "P2", "status": "closed_fixed_and_independently_retested", "original": "report-path-finding-01.json", "resolution": "保留report01，新禁网report02按仓库布局定位原件，32本地链接及摘要均已核"}], "open_findings": [],
    "failures_and_intermediate_observations_retained": [
        "preflight01旧Swagger名称配置假设错误，02按实际配置修正", "build-images01索引/平台ID比较错误，随后按分层身份核证",
        "build-images02/03在21构建依赖失败，本机同配方缓存构建后原样上传，不追认为远端构建成功",
        "report01交付相对链接失效，原件保留，最终report02修正", "live-http-driver01误从I投影取父ID，02误把4副本计入8原答；原http目录保留，http03最终通过",
        "case-r2-reloaded-ax为中间加载态，后续ready-ax才为通过依据",
        "本独立初始包驱动误将JSON重序列化摘要等同原始OCI字节；已移除假设，不作产品失败",
        "本独立初始最终内联驱动只取Case artifact包装，遇A/I metadata时报KeyError；仅驱动修为遵循两种现有包装，未改产品或数据"],
    "actions": {"reviewer_remote_requests": 0, "reviewer_product_changes": 0, "reviewer_deployments": 0, "release_new_ingress": 0, "release_business_posts": 0, "release_new_model_calls": 0, "data_cleanup": 0, "git_commit_or_push": 0},
    "limits": ["仅既有telemetry-channel-02材料在显式兼容配置中的显示；新默认lyc未新投放", "模型原答及4项自动/另存1项人工质量问题保持，不判正文质量通过", "D5/D6及整个change交接/结束审计保持未完成", "保留检查限定本次服务/账本/prepared与目标HTTP，不宣称全库或自然周期行为验收", "浏览器由协调方实际操作，本独立审计核保存证据未重复操作"],
    "final_report": "docs/operations/evidence/workbench-4b-release-20261117-01/report-02/report.md",
    "active_entry": "http://127.0.0.1:4177/viewer/", "evidence": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in refs]}
target = OUT / "independent-release-review-01.json"
with target.open("x") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
assert read(target)["open_findings"] == []
print(json.dumps({"path": str(target), "sha256": sha(target), "status": result["status"], "checks": len(checks), "open_findings": 0}, ensure_ascii=False))
