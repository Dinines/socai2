"""Render one scoped investigation export as a standalone, offline audit page."""
import html
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from processing_audit_delivery import incident_fields
from processing_audit_flow import SOURCES, STATES, TOOLS, render_flow
from processing_audit_inspector import PANEL
from processing_audit_inspector import SCRIPT as INSPECTOR_SCRIPT
from processing_audit_inspector import STYLE as INSPECTOR_STYLE

BEIJING = timezone(timedelta(hours=8))
MODULES = {
    "alert_basic": "A · 告警分诊",
    "incident_diagnosis": "I · 事件诊断",
    "baseline": "C · Case 调查",
    "ai_question": "Q · AI 问答",
}
ARTIFACT_NAMES = {
    "input_snapshot": "执行输入快照", "source_snapshot": "留存的材料或回执",
    "model_request": "模型请求", "model_response": "模型原答或错误回执",
    "tool_request": "查询请求", "tool_response": "查询返回",
    "domain_analysis": "领域分析", "deep_analysis": "问题深查结果",
    "alert_graph": "告警关系图", "report_json": "结构化报告", "report_markdown": "报告正文",
}
STEP_NAMES = {
    ("A", "stage"): "汇总告警分诊", ("A", "model"): "向模型请求分诊",
    ("I", "stage"): "汇总并保存事件诊断", ("I", "model"): "向模型请求事件诊断",
    ("C1.executor", "stage"): "准备本轮执行计划", ("C2", "stage"): "汇总背景信息",
    ("C4.materials", "stage"): "整理主分析要用的材料", ("C3", "stage"): "汇总初次分析",
    ("C3", "model"): "向模型请求初次分析", ("C4.routing", "stage"): "记录每条补查建议的去向",
    ("C4.deep", "stage"): "深查一个具体问题", ("C4.deep", "model"): "请模型决定如何继续深查",
    ("C5", "graph"): "根据已保存的材料构图", ("C6", "stage"): "整理并保存最终交付",
    ("C6", "model"): "向模型请求最终结论", ("C3.reanalysis", "stage"): "补证后重新分析",
    ("C3.reanalysis", "model"): "向模型请求重新分析",
}
TEST_MATERIALS = (
    ("测试前准备了什么", (
        ("plan", "本案测试计划", "列出测试主体和要调查的时间范围。流程图中的颜色由实际执行记录决定。"),
        ("inputs", "投入测试的告警", "这是测试送进去的原始材料。告警分诊和事件诊断各自实际使用的版本，可以在对应轮次的“输入”中查看。"),
        ("lake_rows", "测试日志及核对结果", "这是为本案准备或核对过的日志。要确认调查实际查过哪些日志，请查看流程中的查询步骤及其输出。"),
    )),
    ("测试怎样启动各轮处理", (
        ("receipts", "作业调用及返回", "这里记录测试程序发起了什么调用、处理程序当时怎样返回。实际模型请求和原始答复保存在各步骤的工件里。"),
    )),
    ("执行后查到了什么", (
        ("page_fields", "从数据库整理出的页面字段", "用来核对哪些字段有值、哪些为空。可与前面的正式结果和当前判断对照。"),
        ("page_reads", "通过页面读取方法查到的值", "这是测试完成后再次查询得到的结果。例如，事件诊断发布的摘要能否在事件页面读到。"),
    )),
)


def esc(value):
    return html.escape(str(value), quote=True)


def raw(label, value, *, record=False):
    body = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    attr = ' data-record-json' if record else ''
    return f"<details><summary>{esc(label)}</summary><pre{attr}>{esc(body)}</pre></details>"


def beijing(value):
    if not value:
        return "未记录"
    try:
        stamp = datetime.fromisoformat(value)
        if stamp.utcoffset() is not None:
            return stamp.astimezone(BEIJING).strftime("%Y-%m-%d %H:%M:%S.%f").rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        pass
    return f"{value}（无法换算时区）"


def fields(items):
    pairs = "".join(f"<dt>{esc(label)}</dt><dd>{esc(value) if value is not None else '未记录'}</dd>"
                    for label, value in items)
    return f"<dl>{pairs}</dl>"


def model_excerpt(reply):
    if not isinstance(reply, dict):
        return ""
    choices = reply.get("choices") or []
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        return ""
    try:
        answer = json.loads(content)
    except ValueError:
        return ""
    if isinstance(answer, dict):
        for field in ("summary", "rationale", "conclusion", "answer", "reason"):
            value = answer.get(field)
            if isinstance(value, str) and value.strip():
                return value[:160] + ("…" if len(value) > 160 else "")
    return ""


def artifact_note(artifact):
    kind = artifact.get("kind")
    body = artifact.get("content_json")
    if not isinstance(body, dict):
        return ""
    if kind == "model_request":
        return "发送给模型的请求" + (f' · {body["model"]}' if body.get("model") else "")
    if kind == "model_response":
        reply = body.get("payload", body)
        if not isinstance(reply, dict):
            return ""
        transport = reply.get("transport_error") or {}
        if isinstance(transport, dict) and transport.get("http_status") is not None:
            return f'调用回执 · HTTP {transport["http_status"]}' + (" · 未收到原答" if reply.get("raw") is None else "")
        if reply.get("raw") is not None:
            reason = reply.get("validation_error")
            state = f"模型原答已保存 · 校验错误 {reason}" if reason else "模型原答已保存"
            excerpt = model_excerpt(reply["raw"])
            return f"{state}。原答摘录　{excerpt}" if excerpt else state
    if kind in {"tool_request", "tool_response"}:
        parts = [body.get("tool_name"), body.get("state")]
        if body.get("returned_rows") is not None:
            parts.append(f'返回 {body["returned_rows"]} 行')
        error = body.get("error")
        parts.append(body.get("reason") or (error.get("code") if isinstance(error, dict) else None))
        return " · ".join(str(part) for part in parts if part)
    if body.get("type") == "delivery_report" and isinstance(body.get("result"), dict):
        return body["result"].get("conclusion") or body["result"].get("title") or ""
    result = body.get("output")
    if isinstance(result, dict) and isinstance(body.get("outcome"), dict):
        return result.get("summary") or result.get("rationale") or ""
    return ""


def artifact_ref(identity, directory, *, inline=False):
    if identity is None:
        return '<span class="quiet">未记录</span>'
    match = directory.get(identity)
    if match is None:
        return f'<span class="missing">{esc(identity)}（此快照缺少工件原件）</span>'
    index, artifact = match
    kind = artifact.get("kind")
    label = f'{esc(ARTIFACT_NAMES.get(kind, kind))} · {esc(identity)}'
    if inline:
        note = artifact_note(artifact)
        preview = f'<span class="quiet">{esc(note)}</span>' if note else ""
        return (preview + f'<details class="step-artifact" data-target="artifact-{index}"><summary>{label}</summary>'
                f'<a href="#artifact-{index}">定位到工件原件</a></details>')
    return f'<a href="#artifact-{index}">{label}</a>'


def refs(items):
    return "<dl>" + "".join(f"<dt>{esc(label)}</dt><dd>{markup}</dd>" for label, markup in items) + "</dl>"


def render_step(step, attached, directory, step_anchor):
    pointers = [("输入", "input_artifact_id"), ("输出", "output_artifact_id"), ("复用", "reused_artifact_id")]
    links = []
    for label, field in pointers:
        identity = step.get(field)
        markup = artifact_ref(identity, directory, inline=True)
        if identity is None and label in {"输入", "输出"}:
            markup = f'<span class="quiet">未绑定单独的{label}工件</span>'
        if label == "输入" and step.get("actual_args") is not None:
            markup += raw("实际调用参数", step["actual_args"])
        if label == "输出" and step.get("error") is not None:
            markup += raw("错误回执", step["error"])
        links.append((label, markup))
    linked = {step.get(field) for _, field in pointers}
    other = [artifact_ref(f["id"], directory, inline=True) for f in attached if f["id"] not in linked]
    links.append(("其他关联工件", "<br>".join(other) or '<span class="quiet">无记录</span>'))
    code, kind, name = step.get("stage_code"), step.get("kind"), step.get("name")
    action = STEP_NAMES.get((code, kind), name)
    if kind == "tool":
        tool = (step.get("actual_args") or {}).get("tool_name") or name
        action = "查询" + (SOURCES.get(tool) or TOOLS.get(tool) or str(tool))
    elif name == "system_closing":
        action = "保存系统兜底报告"
    title = f'步骤 {step.get("seq")} · {action}'
    state = esc(STATES.get(step.get("state"), (step.get("state") or "未记录",))[0])
    summary = f'<summary>{esc(title)} <code>{state}</code></summary>'
    facts = [("步骤 ID", step.get("id")), ("流程编号 / 类型", f"{code} / {kind}"), ("程序记录名", name),
             ("开始", beijing(step.get("started_at"))), ("结束", beijing(step.get("ended_at")))]
    if step.get("returned_rows") is not None:
        facts.append(("实际返回行数", step["returned_rows"]))
    if isinstance(step.get("error"), dict):
        facts.append(("错误或跳过原因", step["error"].get("code") or step["error"].get("message")))
    usage = raw("用量", step["usage"]) if step.get("usage") is not None else ""
    return (f'<details class="step" id="{esc(step_anchor)}" data-record-kind="step" data-record-id="{esc(step["id"])}"'
            f' data-run-id="{esc(step.get("run_id") or "")}" data-parent-step-id="{esc(step.get("parent_step_id") or "")}">'
            + summary + refs(links) + fields(facts)
            + usage + raw("步骤记录（数据库 run_steps）", step, record=True) + "</details>")


def frozen_input(run, directory):
    identity = run.get("input_artifact_id")
    match = directory.get(identity)
    source = (match[1].get("content_json") if match else None) or {}
    parts = ["<h4>输入</h4>"]
    if match:
        parts.append("<p>这是本轮开始时保存的材料版本。即使事后修改了告警，这里仍显示当时这轮拿到的内容。</p>")
    if isinstance(source, dict):
        parent = source.get("parent")
        if isinstance(parent, dict) and run.get("kind") == "incident_diagnosis":
            parts.append(fields([("开始时的事件", parent.get("title") or parent.get("id"))]))
        members = source.get("members")
        if isinstance(members, list):
            parts.append(f"<p>当时纳入的告警（{len(members)} 条）</p><ul>")
            for member in members:
                alert = member.get("alert") if isinstance(member, dict) else None
                if isinstance(alert, dict):
                    parts.append("<li>" + esc(alert.get("title") or alert.get("id") or "未记录标题")
                                 + (" · " + esc(alert["severity"]) if alert.get("severity") else "") + "</li>")
            parts.append("</ul>")
        scope = source.get("scope")
        if isinstance(scope, dict) and isinstance(scope.get("alert_ids"), list):
            parts.append(fields([("开始时的调查范围", f'{len(scope["alert_ids"])} 条告警'),
                                 ("调查时间窗（北京）", f'{beijing(scope.get("window_start"))} 至 {beijing(scope.get("window_end"))}')]))
    parts.append(refs([("本轮输入原件", artifact_ref(identity, directory, inline=True))]))
    return "".join(parts)


def stage_outputs(run, run_artifacts, data):
    is_incident = run["kind"] == "incident_diagnosis"
    table = "incident_diagnoses" if is_incident else "alert_assessments"
    noun = "事件诊断" if is_incident else "告警分诊"
    rows = [r for r in data.get(table, ()) if r.get("source_run_id") == run["id"]]
    receipts = {}
    for artifact in run_artifacts:
        body = artifact.get("content_json")
        outcome = body.get("outcome") if isinstance(body, dict) else None
        if isinstance(outcome, dict) and outcome.get("result_id"):
            receipts[outcome["result_id"]] = outcome
    if not rows:
        return f"<p>本轮快照未见{noun}结果。</p>"
    parts = []
    for row in rows:
        receipt = receipts.get(row["id"], {})
        facts = []
        if receipt.get("adopted") is True:
            facts.append(("发布状态", "本轮已发布"))
        elif receipt.get("adopted") is False:
            facts.append(("发布状态", "已保存，本轮未发布"))
            facts.append(("原因", receipt.get("reason")))
        if is_incident:
            facts.append(("诊断记录状态", row.get("state")))
            if row.get("summary"):
                facts.append(("事件诊断摘要", row["summary"]))
            elif row.get("state") != "completed":
                facts.append(("事件诊断摘要", "本轮未保存摘要"))
        else:
            facts.extend([("分诊判断", row.get("verdict")), ("置信度", row.get("confidence")),
                          ("分诊理由", row.get("rationale"))])
        if table == "incident_diagnoses":
            facts.extend(incident_fields(row))
        parts.extend((fields(facts), raw(f"{noun}原始记录（数据库 {table}）", row)))
    return "".join(parts)


def case_outputs(run, run_artifacts, directory, data):
    results = [r for r in data.get("results", ()) if r.get("source_run_id") == run["id"]]
    parts = [f"<p>本轮正式 Result（{len(results)}）</p>"]
    for result in results:
        parts.extend((fields([("结论来源", result.get("conclusion_origin")), ("结论", result.get("conclusion")),
                              ("结果校验", result.get("validation_state")), ("结果交付", result.get("delivery_state"))]),
                      raw("正式结果原始记录（数据库 results）", result)))
    for artifact in run_artifacts:
        body = artifact.get("content_json")
        if isinstance(body, dict) and body.get("type") == "delivery_report":
            parts.append(refs([("本轮交付报告", artifact_ref(artifact["id"], directory, inline=True))]))
    artifacts = {a["id"] for a in run_artifacts}
    result_ids = {r["id"] for r in results}
    sources = [s for s in data.get("case_assessment_sources", ()) if s.get("case_id") == run.get("case_id")
               and (s.get("result_id") in result_ids or s.get("artifact_id") in artifacts)]
    current_ids = {c.get("current_assessment_id") for c in data.get("cases", ()) if c["id"] == run.get("case_id")}
    linked_ids = current_ids.intersection(s.get("assessment_id") for s in sources)
    for current in data.get("case_assessments", ()):
        if current["id"] in linked_ids and current.get("case_id") == run.get("case_id"):
            parts.extend((fields([("引用本轮的当前判断", current.get("conclusion")), ("判断来源", current.get("origin"))]),
                          raw("当前判断来源记录", [s for s in sources if s.get("assessment_id") == current["id"]])))
    return "".join(parts)


def render_run(run, steps, by_step, run_artifacts, directory, titles, run_anchor, step_ids, data):
    rid = run["id"]
    subject = titles.get(run.get("alert_id")) or titles.get(run.get("incident_id")) or titles.get(run.get("case_id"))
    name = run.get("title") or subject or rid
    state = run.get("state") or "未记录"
    delivery = run.get("delivery_state") or "未记录"
    parts = [(f'<details class="run" id="{esc(run_anchor)}" data-record-kind="run" data-record-id="{esc(rid)}"'
              f' data-run-id="{esc(rid)}"><summary>{esc(name)} <code>{esc(state)} / {esc(delivery)}</code></summary>'),
             fields([("Run ID", rid), ("关联主体", subject),
                     ("实际开始", beijing(run.get("started_at"))), ("实际结束", beijing(run.get("ended_at"))),
                     ("请求时间", beijing(run.get("requested_at"))), ("执行状态", state), ("交付状态", delivery),
                     ("停止原因", run.get("stop_reason"))]),
             frozen_input(run, directory), "<h4>输出</h4>"]
    if run.get("kind") in ("alert_basic", "incident_diagnosis"):
        parts.append(stage_outputs(run, run_artifacts, data))
    elif run.get("kind") == "baseline":
        parts.append(case_outputs(run, run_artifacts, directory, data))
    else:
        parts.append("<p>已记录的输出见本轮步骤和关联工件。</p>")
    parts.append(raw("执行记录（数据库 runs）", run, record=True))
    if run.get("kind") == "baseline":
        recorded = {str(s.get("stage_code") or "").split(".")[0] for s in steps}
        absent = [f"C{i}" for i in range(1, 7) if f"C{i}" not in recorded]
        if absent:
            parts.append('<p class="quiet">未见步骤行的阶段　' + "、".join(absent) + "</p>")
    parts.append(f"<h4>步骤（{len(steps)}）</h4>")
    for step in sorted(steps, key=lambda s: (s.get("seq") is None, s.get("seq"), s["id"])):
        parts.append(render_step(step, by_step.get(step["id"], ()), directory, step_ids[step["id"]]))
    if not steps:
        parts.append('<p class="quiet">未记录步骤。</p>')
    other = [artifact_ref(f["id"], directory, inline=True) for f in run_artifacts if f.get("step_id") is None]
    parts.append(refs([("仅绑定 Run 的工件", "<br>".join(other) or '<span class="quiet">无记录</span>')]))
    parts.append('<a href="#flow-map">返回流程图</a>')
    return "".join(parts) + "</details>"


def outcome(data, directory):
    assessments = {a["id"]: a for a in data.get("case_assessments", [])}
    parts = ['<section id="case-results"><h2>正式结果与当前判断</h2>']
    cases = data.get("cases", [])
    if not cases:
        parts.append('<p class="quiet">本次导出未见已建 Case。</p>')
    for case in cases:
        assessment_id = case.get("current_assessment_id")
        current = assessments.get(assessment_id)
        parts.append(fields([("Case ID", case["id"]), ("案件状态", case.get("handling_status")),
                             ("分类", case.get("classification")), ("当前判断 ID", assessment_id)]))
        if current is not None:
            parts.append(fields([("判断来源", current.get("origin")), ("当前结论", current.get("conclusion")),
                                 ("采用时间", beijing(current.get("adopted_at")))]))
            sources = [s for s in data.get("case_assessment_sources", []) if s.get("assessment_id") == assessment_id]
            parts.append(raw(f"本次判断的来源记录（{len(sources)}）", sources))
            for source in sources:
                if source.get("artifact_id"):
                    parts.append(refs([("判断来源工件", artifact_ref(source["artifact_id"], directory))]))
        elif assessment_id is not None:
            parts.append('<p class="missing">此快照缺少当前判断原件。</p>')
        else:
            parts.append('<p class="quiet">未记录当前判断。</p>')
        parts.append(refs([("当前证据目录", artifact_ref(case.get("current_evidence_artifact_id"), directory))]))
    results = data.get("results", [])
    parts.append(f"<h3>正式 Result（{len(results)}）</h3>")
    for result in results:
        parts.append(fields([("Result ID", result["id"]), ("对应 Run", result.get("source_run_id")),
                             ("结论来源", result.get("conclusion_origin")), ("交付状态", result.get("delivery_state")),
                             ("校验状态", result.get("validation_state")), ("结论", result.get("conclusion"))]))
        parts.append(refs([(label, artifact_ref(result.get(field), directory))
                           for label, field in (("结果输入", "input_artifact_id"), ("结果报告", "report_artifact_id"),
                                                ("结果图谱", "graph_artifact_id"))]))
    if not results:
        parts.append('<p class="quiet">未保存正式 Result。</p>')
    return "".join(parts) + "</section>"


def test_materials(extras):
    parts = ['<section id="test-materials"><h2>测试准备、调用与事后核对</h2>',
             ('<p>这里保存测试人员或测试程序在流程外留下的记录。查某一步实际用了什么、产生了什么，请看'
              '<a href="#execution-records">执行记录</a>；核对发布结果，请看<a href="#case-results">正式结果与当前判断</a>。</p>')]
    known = set()
    for heading, entries in TEST_MATERIALS:
        available = [(key, title, note) for key, title, note in entries if key in extras]
        if available:
            parts.append(f"<h3>{esc(heading)}</h3>")
        for key, title, note in available:
            known.add(key)
            parts.append(f'<p class="source-note"><strong>{esc(title)}</strong> · {esc(note)}</p>')
            parts.append(raw("查看原文 · " + title, extras[key]))
    parts.extend(raw(key, value) for key, value in extras.items() if key not in known)
    return "".join(parts) + "</section>"


def flow_map(modules, by_run, steps_by_run, directory, run_ids, step_ids, titles):
    kinds = list(dict.fromkeys(["baseline", "alert_basic", "incident_diagnosis", *modules]))
    buttons, choices, panels = [], [], []
    default_kind = next((k for k in ["baseline", "incident_diagnosis", "alert_basic", *kinds] if modules.get(k)), "baseline")
    for group, kind in enumerate(kinds):
        runs = sorted(modules.get(kind, []), key=lambda r: (r.get("requested_at") or "", r["id"]))
        active = kind == default_kind
        group_label = MODULES.get(kind, kind)
        buttons.append(f'<button type="button" data-group="{group}" aria-pressed="{str(active).lower()}">'
                       f'{esc(group_label)}</button>')
        default_run = runs[-1] if runs else None
        options = []
        for i, run in enumerate(runs or [{"id": None, "kind": kind}]):
            rid = run["id"]
            selected = run == default_run or not runs
            panel = f"map-{group}-{i}"
            title = next((titles.get(run.get(field)) for field in ("alert_id", "incident_id", "case_id")
                          if titles.get(run.get(field))), None)
            state = STATES.get(run.get("state"), (run.get("state") or "未记录",))[0]
            when = beijing(run.get("started_at") or run.get("requested_at"))
            label = f'第 {i+1} 轮 · {title or run.get("title") or group_label} · {state} · {when}' if runs else "未记录执行"
            options.append(f'<option value="{panel}"{" selected" if selected else ""}>{esc(label)}</option>')
            contents = render_flow(run, steps_by_run.get(rid, []), by_run.get(rid, []), directory, step_ids, run_ids.get(rid))
            panels.append(f'<div class="flow-panel" id="{panel}" data-run-id="{esc(rid or "")}"'
                          f'{"" if active and selected else " hidden"}>{contents}</div>')
        choices.append(f'<label class="flow-choice" data-choice="{group}"{"" if active else " hidden"}>'
                       f'查看执行 <select aria-label="{esc(group_label)}的轮次">{"".join(options)}</select></label>')
    return ('<section id="flow-map" aria-labelledby="flow-title"><h2 id="flow-title">调查流程图</h2>'
            '<p class="quiet">选择一轮执行，点击节点查看提示词、输入、输出和失败原因。</p>'
            '<div class="flow-workspace"><div class="flow-navigation">'
            '<div class="flow-modules" aria-label="模块">' + "".join(buttons) + '</div>' + "".join(choices)
            + '<div class="flow-legend"><span class="is-success">成功</span><span class="is-failed">失败</span>'
            '<span class="is-unknown">待确认 / 进行中</span><span class="is-idle">未走 / 跳过</span></div>'
            + "".join(panels) + '</div>' + PANEL + '</div></section>')


STYLE = """
*{box-sizing:border-box}html{color-scheme:light}body{margin:0;color:#17372e;background:white;
font:15px/1.6 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1000px;margin:auto;padding:24px clamp(12px,3vw,32px)}
h1{line-height:1.25;font-size:clamp(22px,4vw,32px);margin:.2em 0}h2{font-size:20px;margin:0 0 10px}
h3{font-size:16px;margin:16px 0 4px}h4{margin:.7em 0 .2em}section{border-top:1px solid #d9e5dd;margin-top:22px;padding-top:16px}
p{margin:.4em 0}.quiet,dt{color:#50645d}.missing{color:#8a5423}a{color:#0a6652;text-underline-offset:3px}
summary{cursor:pointer;padding:.25em 0;color:#184e3f}details{margin:.28em 0;overflow-wrap:anywhere}
details[open]>summary{font-weight:650}details.run,details.step{border:1px solid #d6e2da;padding:7px 12px;border-radius:5px}
details.run{margin:8px 0}details.step{margin:6px 0;background:#fcfdfc}code{font-size:.85em;color:#315c4e}
dl{display:grid;grid-template-columns:minmax(6em,10em) minmax(0,1fr);gap:2px 10px;margin:.4em 0 1em}
dd{margin:0;overflow-wrap:anywhere;white-space:pre-wrap}pre{background:#f2f6f3;border-radius:4px;padding:10px;
white-space:pre-wrap;overflow-wrap:anywhere;max-height:32em;overflow:auto;font:12px/1.55 Consolas,monospace}
.record:target{outline:2px solid #439079;outline-offset:1px}.record{padding:2px 6px}
.files-head,.subject-links,.recent-line{display:flex;align-items:baseline;flex-wrap:wrap;gap:5px 14px}
.files-head{justify-content:space-between}.files-head h2{margin:0}.recent-line{padding:4px 0}
.recent-line time,.subject-links{font-size:13px;color:#50645d}
.recent-line time{font-variant-numeric:tabular-nums}.recent-line a,.subject-links a{overflow-wrap:anywhere}
details.run:target,details.step:target{outline:2px solid #39836f;outline-offset:2px}
.source-note{margin-top:.85em}.flow-modules{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:12px 0}
.flow-modules button,.flow-choice select{font:inherit;color:#23473d;background:white;border:1px solid #a4b8ad;border-radius:5px;padding:5px 9px}
.flow-modules button{cursor:pointer}.flow-modules button[aria-pressed=true]{background:#234f42;color:white;border-color:#234f42}
.flow-choice{color:#425a51;font-size:13px}.flow-choice select{max-width:100%;font-size:13px;padding:3px}
.flow-legend{display:flex;gap:6px 13px;flex-wrap:wrap;color:#43564f;font-size:12px;margin:10px 0}
.flow-legend span::before{content:"";display:inline-block;width:.72em;height:.72em;background:var(--fill);border:1px solid var(--stroke);border-radius:2px;margin-right:4px}
.is-success{--fill:#def3e7;--stroke:#77b492;--ink:#17472e}
.is-failed{--fill:#fbe1df;--stroke:#cf8986;--ink:#792b29}
.is-unknown,.is-active{--fill:#fff1d6;--stroke:#c7a563;--ink:#674911}
.is-idle{--fill:#fff;--stroke:#c8d2ce;--ink:#55635b}
.flow-lanes{list-style:none;margin:0;padding:0;--spine:#afc6ba}
.flow-lane{position:relative;display:grid;grid-template-columns:minmax(135px,36%) minmax(0,1fr);align-items:center;padding:5px 0;gap:16px}
.flow-lane:not(:last-child)::after{content:"";position:absolute;left:18%;width:2px;top:50%;bottom:-50%;background:var(--spine);pointer-events:none}
.flow-main,.flow-branches{z-index:1;display:flex;flex-wrap:wrap;gap:4px}.flow-main{flex-direction:column}
.flow-branches{position:relative;padding:3px 0 3px 9px;border-left:1px solid var(--spine)}
.flow-deep-actions{display:flex;flex:1 1 100%;flex-wrap:wrap;gap:4px}
.flow-branches::before{content:"";position:absolute;left:-17px;top:50%;width:16px;height:1px;background:var(--spine)}
.flow-node{display:inline-block;max-width:100%;padding:4px 8px;border:1px solid var(--stroke);border-radius:5px;background:var(--fill);color:var(--ink);font-size:13px;line-height:1.5;overflow-wrap:anywhere;text-decoration:none}
.flow-main .flow-node{padding:6px 8px}.flow-node:is(.is-failed,.is-success,.is-active,.is-unknown){font-weight:650}
a.flow-node:hover,a.flow-node:focus-visible{text-decoration:underline;outline:2px solid var(--ink);outline-offset:1px}
[hidden]{display:none!important}.flow-panel{margin:8px 0 0}.flow-panel:focus-visible{outline:2px solid #396e60}
@media(max-width:520px){.flow-lane{grid-template-columns:minmax(95px,37%) minmax(0,1fr);gap:10px}.flow-node{font-size:12px;padding:3px 5px}.flow-branches{padding-left:6px}.flow-branches::before{left:-11px;width:10px}}
@media(max-width:440px){main{padding:13px 9px}dl{grid-template-columns:5.5em minmax(0,1fr)}details.run,details.step{padding:5px 7px}}
"""


def recent_files(logs):
    if not logs:
        return ""
    parts = ['<section id="log-files"><div class="files-head"><h2>最近步骤日志</h2>',
             f'<a target="_blank" rel="noopener" href="../{esc(logs["index"])}">全部轮次与文件 ↗</a></div>']
    for item in logs["recent"]:
        state = STATES.get(item.get("state"), (item.get("state") or "未记录",))[0]
        parts.append(f'<div class="recent-line"><time>{esc(beijing(item.get("updated_at")))}</time>'
                     f'<a target="_blank" rel="noopener" href="../{esc(item["path"])}">{esc(item["label"])}</a>'
                     f'<span>{esc(state)}</span></div>')
    if not logs["recent"]:
        parts.append("<p>当前快照还没有 Case 步骤记录。</p>")
    return "".join(parts) + "</section>"


def render_case_detail(*, key: str, title: str, batch: str, data: dict, extras: dict, logs=None, subjects=()) -> str:
    """Use only the supplied snapshot. Links reference local, generated numeric anchors."""
    artifacts = data.get("artifacts", [])
    directory = {f["id"]: (i, f) for i, f in enumerate(artifacts)}
    by_step, by_run, steps_by_run, modules = (defaultdict(list) for _ in range(4))
    for f in artifacts:
        by_step[f.get("step_id")].append(f)
        by_run[f.get("run_id")].append(f)
    for step in data.get("run_steps", []):
        steps_by_run[step.get("run_id")].append(step)
    for run in data.get("runs", []):
        modules[run.get("kind") or "未标注模块"].append(run)
    run_ids = {r["id"]: f"run-{i}" for i, r in enumerate(data.get("runs", []))}
    step_ids = {s["id"]: f"step-{i}" for i, s in enumerate(data.get("run_steps", []))}
    titles = {r["id"]: r.get("title") for table in ("alerts", "incidents", "cases") for r in data.get(table, [])}
    view = ['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width,initial-scale=1">',
            (f'<title>{esc(title)} · 调查执行明细</title><style>{STYLE}{INSPECTOR_STYLE}</style>'
             '</head><body><main class="workbench-detail">'),
            f'<header><p class="quiet">{esc(batch)} · {esc(key)}</p><h1>{esc(title)}</h1>',
            "".join(f'<p class="quiet">Case ID <code>{esc(row["id"])}</code></p>' for row in data.get("cases", ())),
            '<p class="quiet">执行时间为北京时间（UTC+8）。</p>',
            '<div class="subject-links">' + "".join(
                f'<a href="../{esc(s["detail"])}" target="_blank" rel="noopener">'
                f'{"告警" if s["kind"] == "alert" else "事件"} · {esc(s["title"])}</a>' for s in subjects
            ) + '</div></header>',
            recent_files(logs),
            flow_map(modules, by_run, steps_by_run, directory, run_ids, step_ids, titles),
            '<section id="execution-records"><h2>各轮执行的输入与输出</h2>',
            '<p class="quiet">一轮执行对应一次分诊、诊断或调查；一轮里面可以有多个步骤。</p>']
    for kind in dict.fromkeys(["baseline", *MODULES, *modules]):
        if not modules[kind] and kind not in ("alert_basic", "incident_diagnosis", "baseline"):
            continue
        view.append(f"<h3>{esc(MODULES.get(kind, kind))}（{len(modules[kind])} 轮）</h3>")
        if not modules[kind]:
            view.append('<p class="quiet">未记录此类 Run。</p>')
        for run in sorted(modules[kind], key=lambda r: (r.get("requested_at") or "", r["id"])):
            view.append(render_run(run, steps_by_run[run["id"]], by_step, by_run[run["id"]], directory, titles,
                                   run_ids[run["id"]], step_ids, data))
    view.extend(["</section>", outcome(data, directory), f'<section id="artifacts"><h2>工件原件（{len(artifacts)}）</h2>',
                 ('<p>工件是处理时实际保存的一份材料，例如发给模型的请求、模型原答或错误回执。'
                  '上面步骤中展开的输入或输出与这里同 ID 的原件是同一份。</p>')])
    for i, f in enumerate(artifacts):
        label = f'{f.get("kind")} · {f["id"]}'
        body = esc(json.dumps(f, ensure_ascii=False, indent=2, allow_nan=False))
        view.append(f'<details id="artifact-{i}" class="record" data-record-kind="artifact" data-record-id="{esc(f["id"])}"'
                    f' data-run-id="{esc(f.get("run_id") or "")}" data-step-id="{esc(f.get("step_id") or "")}">'
                    f'<summary>{esc(label)}</summary><pre data-record-json>{body}</pre></details>')
    if not artifacts:
        view.append('<p class="quiet">未记录工件。</p>')
    view.append('</section><section id="database-rows"><h2>数据库里的业务记录</h2>'
                '<p>按表核对告警、事件、已发布的诊断和案件判断。每轮及每步的状态行可在上方的执行记录里查看。</p>')
    for table, rows in data.items():
        if table not in {"runs", "run_steps", "artifacts"}:
            view.append(raw(f"{table}（{len(rows)}）", rows))
    orphan_steps = [s for s in data.get("run_steps", []) if s.get("run_id") not in run_ids]
    if orphan_steps:
        view.append(raw("未找到所属 Run 的步骤", orphan_steps))
    view.append("</section>")
    if extras:
        view.append(test_materials(extras))
    # Native anchors retain a working target even in a script-disabled iframe.
    view.append("""</main><script>
document.addEventListener("toggle", event => {
    const panel = event.target;
    if (!panel.matches("details.step-artifact") || !panel.open || panel.querySelector("pre")) return;
    const source = document.getElementById(panel.dataset.target).querySelector("pre");
    panel.querySelector("summary").after(source.cloneNode(true));
}, true);
const flow = document.getElementById("flow-map");
function choose(group) {
    resetInspector();
    let panelId;
    for (const button of flow.querySelectorAll("[data-group]")) {
        button.setAttribute("aria-pressed", String(button.dataset.group === group));
    }
    for (const choice of flow.querySelectorAll("[data-choice]")) {
        choice.hidden = choice.dataset.choice !== group;
        if (!choice.hidden) panelId = choice.querySelector("select").value;
    }
    for (const panel of flow.querySelectorAll(".flow-panel")) panel.hidden = panel.id !== panelId;
}
flow.addEventListener("click", event => {
    const button = event.target.closest("[data-group]");
    if (button) choose(button.dataset.group);
});
flow.addEventListener("change", event => {
    const choice = event.target.closest("[data-choice]");
    if (choice) choose(choice.dataset.choice);
});
function showRecord() {
    const id = location.hash.slice(1);
    if (!/^(artifact|step|run)-[0-9]+$/.test(id)) return;
    const record = document.getElementById(id);
    if (!record) return;
    for (let el = record; el; el = el.parentElement) {
        if (el.tagName === "DETAILS") el.open = true;
    }
    record.scrollIntoView({block: "start"});
}
window.addEventListener("hashchange", showRecord);
document.addEventListener("click", event => {
    const link = event.target.closest("a[href^='#']");
    if (link && !event.defaultPrevented && link.hash === location.hash) showRecord();
});
showRecord();
""" + INSPECTOR_SCRIPT + "</script></body></html>")
    return "".join(view)
