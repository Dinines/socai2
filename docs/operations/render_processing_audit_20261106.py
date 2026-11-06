"""Render the scoped PG snapshots and dispatch receipts as a self-contained, offline audit."""
import argparse
import html
import json
from collections import Counter
from pathlib import Path

LABEL = {"alert_basic": "A · 告警分诊", "incident_diagnosis": "I · 事件诊断", "baseline": "C · Case 调查"}


def read(path):
    return json.loads(path.read_bytes())


def esc(value):
    return html.escape(str(value))


def detail(label, obj):
    pretty = json.dumps(obj, indent=2, ensure_ascii=False)
    return f"<details><summary>{esc(label)}</summary><pre>{esc(pretty)}</pre></details>"


def pairs(items):
    return "<dl>" + "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in items) + "</dl>"


def stage_rows(run, data, artifacts):
    steps = sorted((s for s in data["run_steps"] if s["run_id"] == run["id"]), key=lambda s: s["seq"])
    sections = []
    for s in steps:
        body = detail("步骤记录 · 参数、时间、用量、错误", s)
        linked = set()
        for label, field in (("输入", "input_artifact_id"), ("输出", "output_artifact_id"), ("复用", "reused_artifact_id")):
            fid = s.get(field)
            if fid and fid in artifacts:
                f = artifacts[fid]
                body += detail(label + " · " + f["kind"], f)
                linked.add(fid)
        for f in artifacts.values():
            if f["step_id"] == s["id"] and f["id"] not in linked:
                body += detail("关联工件 · " + f["kind"], f)
        label = f'{s["seq"]}　{s["stage_code"]}　{s["name"]}'
        sections.append(f'<article><div><strong>{esc(label)}</strong> <code>{esc(s["state"])}</code></div>{body}</article>')
    return "".join(sections)


def render_case(plan, data, pg, inputs, calls, lake, page_reads):
    key = plan["key"]
    files = {f["id"]: f for f in data["artifacts"]}
    title_by_id = {a["id"]: a["title"] for a in data["alerts"]}
    rows = ['<section id="' + key + '"><h2>' + esc(key.upper() + " · " + plan["title"]) + "</h2>"]
    rows.append(pairs([("事件 UUID", plan["incident_id"]), ("Case UUID（实际）",
                data["cases"][0]["id"] if data["cases"] else "本次未建案"),
                ("主机 / 调查时间窗", f'{plan["hostname"]}　{plan["window_start"]} 至 {plan["window_end"]}')]))
    rows += [detail("接收输入 · 原始合成告警及明确归并关系", inputs[key]),
             detail("告警与事件落库 · 最新原件、成员、对象、来源引用", {k: data[k] for k in
                    ("alerts", "alert_materials", "alert_objects", "alert_source_refs", "incidents", "incident_alerts")}),
             detail("验证湖 · 本案已逐值比对的实际行", [r for r in lake["rows"] if
                    r["event_id"] in {e["event_id"] for e in plan.get("lake_events", [])}]),
             detail("按需作业 · 调用参数及返回回执", calls),
             detail("21 页面取数方法返回 · 原件、分诊、事件详情、调查资格", page_reads),
             detail("数据库对照 · 发布指针、Case 当前判断与正式结果", pg)]
    for run in sorted(data["runs"], key=lambda r: r["requested_at"]):
        label = LABEL.get(run["kind"], run["kind"])
        if run["alert_id"]:
            label += " · " + title_by_id.get(run["alert_id"], run["alert_id"])
        rows += ["<h3>" + esc(label) + "</h3>", pairs([("Run", run["id"]),
                 ("执行 / 交付", f'{run["state"]} / {run["delivery_state"]}'), ("停止原因", run["stop_reason"] or "未记录")])]
        if run["input_artifact_id"] in files:
            rows.append(detail("整轮冻结输入", files[run["input_artifact_id"]]))
        stages = [s for s in data["run_steps"] if s["run_id"] == run["id"]]
        if run["kind"] == "baseline":
            present = {s["stage_code"].split(".")[0] for s in stages}
            rows.append("<p>本轮未见步骤行的阶段　" + esc("、".join(c for c in ["C1", "C2", "C3", "C4", "C5", "C6"]
                        if c not in present) or "各阶段均有步骤行") + "。步骤有记录时请核对其状态和实际输出。</p>")
        rows.append(stage_rows(run, data, files))
        rows.append(detail("本轮全部工件目录（含仅绑定 Run 的工件）", [
            {k: f[k] for k in ("id", "kind", "schema_version", "step_id", "sha256", "size_bytes")}
            for f in files.values() if f["run_id"] == run["id"]]))
        for f in files.values():
            if f["run_id"] == run["id"] and f["step_id"] is None and f["id"] != run["input_artifact_id"]:
                rows.append(detail("Run 级工件 · " + f["kind"], f))
    rows.append(detail("最终落库 · 发布、判断、覆盖、活动与任务", {k: data[k] for k in (
        "alert_assessments", "incident_diagnoses", "case_assessments", "case_assessment_sources", "case_assessment_members",
        "case_alerts", "case_incidents", "results", "result_members", "tasks", "task_revisions", "activities") if k in data}))
    rows.append("</section>")
    return "".join(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("batch", type=Path)
    p.add_argument("snapshot", type=Path)
    p.add_argument("receipts", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    if args.output.exists() and 'id="audit-records"' in args.output.read_text(encoding="utf-8"):
        p.error("This output holds the test history. Use update_processing_audit.py --batch <batch-directory>.")
    plan = read(args.batch / "plan.json")
    inputs = read(args.batch / "inputs.json")
    page_reads = read(args.batch / "page-service-readback.json")
    lake = read(args.receipts / "lake-output.json")
    summary = read(args.snapshot / "summary.json")
    gateway = read(args.batch / "gateway-timeout.json")
    model = read(args.batch / "model43-windows.json")
    sections, rows, links = [], [], []
    for case in plan["cases"]:
        key = case["key"]
        data = read(args.snapshot / key / "database.json")
        page = read(args.snapshot / key / "page-fields.json")
        calls = {f.stem: read(f) for f in sorted((args.receipts / key).glob("*.json"))}
        sections.append(render_case(case, data, page, inputs, calls, lake, page_reads[key]))
        order = {s: i for i, s in enumerate(case["alert_ids"])}
        a = sorted([r for r in data["runs"] if r["kind"] == "alert_basic"], key=lambda r: order[r["alert_id"]])
        i = [r for r in data["runs"] if r["kind"] == "incident_diagnosis"]
        c = [r for r in data["runs"] if r["kind"] == "baseline"]
        def states(rs):
            return "、".join(r["state"] for r in rs) or "未执行"
        current = [x for x in data["case_assessments"] if any(k["current_assessment_id"] == x["id"] for k in data["cases"])]
        result = "、".join(str(r["conclusion_origin"]) for r in data["results"]) or "无"
        entries = [key.upper(), states(a), states(i), states(c), result, "、".join(x["origin"] for x in current) or "无"]
        errors = []
        baseline_ids = {r["id"] for r in c}
        for f in data["artifacts"]:
            body = f["content_json"] or {}
            if f["kind"] == "model_response" and f["run_id"] in baseline_ids:
                error = (body.get("payload") or {}).get("transport_error") or {}
                if error.get("status_code") == 408 or str((error.get("fields") or {}).get("code")) == "408":
                    errors.append("C3 网关等待 " + str(int(gateway["global_request_timeout_seconds"])) + " 秒超时 · HTTP 408")
        rows.append("<tr>" + "".join("<td>" + esc(x) + "</td>" for x in entries[:3])
                    + "<td>" + esc(entries[3]) + ("<br><small>" + esc("；".join(errors)) + "</small>" if errors else "")
                    + "</td>" + "".join("<td>" + esc(x) + "</td>" for x in entries[4:]) + "</tr>")
        links.append('<a href="#' + key + '">' + esc(key.upper() + " " + case["title"]) + "</a>")
    counts = Counter()
    for row in summary["cases"]:
        counts.update(row["counts"])
    head = """<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>21 调查处理模块 · 逐阶段审计</title><style>
*{box-sizing:border-box}body{margin:0;background:#f5f6f4;color:#182a29;font:16px/1.65 "Microsoft YaHei",system-ui,sans-serif}
main{max-width:1150px;margin:auto;padding:36px 24px}h1{font-size:clamp(28px,4vw,44px);margin:0}h2{margin:0 0 14px}
h3{margin:28px 0 4px;color:#215753}a,summary{color:#185951}a{margin-right:1.3em}section,header{padding:24px;background:white;border:1px solid #cfd9d4;margin:16px 0}
article{border-left:3px solid #a6c4bb;margin:14px 0;padding:4px 16px}code{color:#633b38;font-family:monospace}summary{cursor:pointer}
details{margin:.45em 0}dl{display:grid;grid-template-columns:minmax(100px,180px) 1fr;gap:2px 10px}dt{color:#566461}dd{margin:0;overflow-wrap:anywhere}
pre{background:#f3f6f4;white-space:pre-wrap;overflow-wrap:anywhere;max-height:32em;overflow-y:auto;padding:12px;font:13px/1.4 Consolas,monospace}
.table{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:8px 12px;border-bottom:1px solid #d4ddd8;text-align:left}
@media(max-width:620px){main{padding:10px}section,header{padding:12px}dl{display:block}dd{margin-bottom:6px}}</style><main>"""
    view = (head + "<header><h1>21 调查处理模块 · 逐阶段审计</h1><p>2026-11-06 · processing-20261106-r3 · "
         + esc(plan["batch"]) + "</p><p>三个新案例共保存 " + str(counts["runs"]) + " 个 Run、"
         + str(counts["run_steps"]) + " 条步骤和 " + str(counts["artifacts"])
         + " 份工件。展开各步可核对输入、模型原答或错误回执，再回到同一主体的发布记录。</p><nav>"
         + "".join(links) + '</nav><div class="table"><table><tr><th>案例</th><th>告警分诊</th><th>事件诊断</th>'
         + "<th>Case 执行</th><th>正式 Result 来源</th><th>当前判断来源</th></tr>" + "".join(rows)
         + "</table></div><p>unknown 表示执行结果待确认。工件、正式 Result 与 Case 当前判断分别读取。"
         + "本批三案均收到 408，未收到 C3 原答；系统已另存待核结论，模型覆盖为零。用量为 null 表示未知。</p>"
         + "<p>21 调查作业 → 21 模型网关 → 43 上的 vLLM / " + esc(model["model"])
         + "。三次调用期间，43 的运行采样均为 1 个执行、0 个等候，稳定生成时约 51 tokens/s。"
         + '这是服务级采样；逐请求完成状态仍以调查回执为准。</p><a href="controls.html">查看 C4、C5、C6 与人工反馈的受控对照</a></header>'
         + "".join(sections) + "</main></html>")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(view, encoding="utf-8")
    ctrl = args.batch / "contract-controls-02"
    db = read(ctrl / "database.json")
    files = {f["id"]: f for f in db["artifacts"]}
    control = [head, ('<header><h1>调查后半段 · 受控对照</h1><p>21 的 r3 处理镜像、真实临时 PostgreSQL；'
               '模型答复与湖查询结果由测试指定。此处查看深查、图、正式结果与人工版本的落库能力。</p>'
               '<a href="index.html">返回三个真实模型案例</a></header>'), detail("执行回执与资源清理", read(ctrl / "receipt.json"))]
    for run in db["runs"]:
        if not any(s["run_id"] == run["id"] for s in db["run_steps"]):
            continue
        control.extend(["<section><h2>" + esc(run["kind"] + " · " + run["state"]) + "</h2>",
            pairs([("Case", run["case_id"]), ("Run", run["id"]), ("停止原因", run["stop_reason"])]),
            detail("冻结输入", files.get(run["input_artifact_id"])), stage_rows(run, db, files),
            detail("正式 Result", [r for r in db["results"] if r["source_run_id"] == run["id"]]), "</section>"])
    control.append(detail("人工任务与版本", {k: db[k] for k in ("tasks", "task_revisions")}))
    args.output.with_name("controls.html").write_text("".join(control) + "</main></html>", encoding="utf-8")


if __name__ == "__main__":
    main()
