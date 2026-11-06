"""Evidence-linked execution lanes for one Run in an offline audit detail."""
import html
import re

STATES = {
    "completed": ("已完成", "success"), "saved": ("已保存", "success"), "selected": ("已登记", "success"),
    "failed": ("失败", "failed"), "timeout": ("超时", "failed"), "unknown": ("结果待确认", "unknown"),
    "running": ("执行中", "active"), "scheduled": ("已安排", "active"), "planned": ("已计划", "idle"),
    "pending_update": ("待启动", "idle"), "skipped": ("已跳过", "idle"), "cancelled": ("已取消", "idle"),
    "handoff": ("待人工确认", "unknown"), "no_route": ("无此分派", "idle"), "missing": ("未记录", "idle"),
    "applicable": ("适用", "success"), "not_applicable": ("不适用", "idle"), "undetermined": ("适用性未定", "unknown"),
    "partial": ("部分交付", "unknown"), "complete": ("完整交付", "success"), "none": ("无交付", "idle"),
}
SOURCES = {"assets": "资产", "history": "历史告警", "threat_intel": "威胁情报", "ueba": "用户行为",
           "knowledge": "知识库", "graph": "身份图"}
DOMAINS = {"identity": "身份", "cloud": "云", "phishing": "钓鱼", "insider": "内部风险"}
MODES = {"query": "直接查询", "deep": "问题深查", "graph": "构图", "human": "人工确认"}
TOOLS = {"process_activity": "进程活动", "network_connections": "网络连接", "authentication_activity": "认证活动",
         "product_host_details": "产品主机详情"}


def node(label, state=None, anchor=None, *, reason=None, note=None):
    state = state or "missing"
    word, color = STATES.get(state, (state, "idle"))
    text = f"{label} · {word}" + (f"（{note}）" if note else "")
    attrs = f'class="flow-node is-{color}"'
    if reason:
        attrs += f' title="{html.escape(str(reason), quote=True)}"'
    text = html.escape(str(text))
    if anchor and re.fullmatch(r"(?:step|artifact|run)-[0-9]+", anchor):
        return f'<a {attrs} href="#{anchor}">{text}</a>'
    return f"<span {attrs}>{text}</span>"


def lane(main, branches=()):
    branch = '<div class="flow-branches">' + "".join(branches) + "</div>" if branches else ""
    return '<li class="flow-lane"><div class="flow-main">' + "".join(main) + "</div>" + branch + "</li>"


def render_flow(run, steps, artifacts, artifact_indices, step_ids, run_anchor):
    """Only links into the current detail. Stage and source names never supply HTML or URLs."""
    steps = sorted((s for s in steps if s.get("run_id") == run["id"]), key=lambda s: s["seq"])
    artifacts = [f for f in artifacts if f.get("run_id") == run["id"]]
    files = {f["id"]: f for f in artifacts}

    def art_anchor(fid):
        if fid in files and fid in artifact_indices:
            return f"artifact-{artifact_indices[fid][0]}"
        return None

    def payload(fid):
        value = files.get(fid, {}).get("content_json")
        return value if isinstance(value, dict) else {}

    def select(code, kind, name=None):
        return [s for s in steps if s.get("stage_code") == code and s.get("kind") == kind
                and (name is None or s.get("name") == name)]

    def step_node(label, s, note=None):
        err = s.get("error") or {}
        reason = err.get("code") if isinstance(err, dict) else err
        return node(label, s.get("state"), step_ids.get(s["id"]), reason=reason, note=note)

    def step_nodes(label, matches):
        return [step_node(label, s) for s in matches] or [node(label)]

    def backgrounds(code, names):
        result = []
        for name in names:
            matches = select(code, "tool", name)
            if not matches:
                result.append(node(SOURCES[name]))
            for s in matches:
                count = s.get("returned_rows")
                result.append(step_node(SOURCES[name], s, f"{count} 行" if count is not None else None))
        return result

    def model(code, label):
        return step_nodes(label, select(code, "model"))

    def domain_outputs(matches):
        found = []
        producer_ids = {s["id"] for s in matches}
        producer_ids.update(s["id"] for s in steps if s.get("parent_step_id") in producer_ids and s["kind"] == "model")
        for domain, label in DOMAINS.items():
            recorded_ids = {(payload(s.get("output_artifact_id")).get("domain_artifact_ids") or {}).get(domain)
                            for s in matches}
            relevant = [f for f in artifacts if (f.get("step_id") in producer_ids or f["id"] in recorded_ids)
                        and f.get("kind") == "domain_analysis" and payload(f["id"]).get("domain") == domain]
            if not relevant:
                found.append(node(label))
            for f in relevant:
                value = payload(f["id"]).get("applicability")
                found.append(node(label, value or "saved", art_anchor(f["id"]),
                                  note=None if value else "未记适用性"))
        return found

    def query_node(s):
        args = s.get("actual_args") or {}
        name = args.get("tool_name") or "查询"
        parents = {p["id"] for p in select("C4.deep", "stage")}
        prefix = "深查查询" if s.get("parent_step_id") in parents else "查询工具"
        count = s.get("returned_rows")
        return step_node(f"{prefix} · {TOOLS.get(name, name)}", s, f"{count} 行" if count is not None else None)

    def routing():
        dispatch = select("C4.routing", "stage")
        actual = []
        receipt_seen = False
        for s in dispatch:
            fid = s.get("output_artifact_id")
            body = payload(fid)
            if body.get("type") == "followup_dispatch" and isinstance(body.get("routes"), list):
                receipt_seen = True
                actual.extend((rt, fid) for rt in body["routes"])
        branches = []
        for mode, label in MODES.items():
            hits = [(rt, fid) for rt, fid in actual if rt.get("mode") == mode]
            if not hits:
                branches.append(node(label, "no_route" if receipt_seen else "missing"))
            for rt, fid in hits:
                notes = []
                if len(actual) > 1 and isinstance(rt.get("followup_index"), int):
                    notes.append(f'建议 {rt["followup_index"] + 1}')
                if rt.get("reused"):
                    notes.append("复用")
                if mode == "deep" and rt.get("answer_available") is False:
                    notes.append("无回答")
                record_key = {"query": "query_artifact_id", "deep": "deep_artifact_id", "graph": "graph_artifact_id"}.get(mode)
                target = art_anchor(rt.get(record_key)) or art_anchor(fid)
                branches.append(node(label, rt.get("state"), target, reason=rt.get("reason"),
                                     note="、".join(notes)))
        for s in steps:
            if s.get("stage_code") == "C4.query" and s.get("kind") == "tool":
                branches.append(query_node(s))
            elif s.get("stage_code") == "C4.deep" and s.get("kind") == "stage":
                summary = payload(s.get("output_artifact_id"))
                answer = summary.get("answer") or {}
                answer_label = {"supported": "有依据", "unresolved": "待核实"}.get(answer.get("state"))
                branches.append(step_node("深查执行", s, answer_label))
                iterations = summary.get("iterations") or []
                calls = [m for m in select("C4.deep", "model") if m.get("parent_step_id") == s["id"]]
                if iterations or calls:
                    actions = []
                    for choice, label in (("query", "再查"), ("answer", "回答"), ("handoff", "交接")):
                        hits = [it for it in iterations if it.get("action") == choice]
                        if not hits:
                            actions.append(node(f"深查模型 · {label}"))
                        for it in hits:
                            target = art_anchor(it.get("response_id")) or step_ids.get(it.get("model_step_id"))
                            actions.append(node(f"深查模型 · {label}", "selected", target or step_ids.get(s["id"])))
                    branches.append('<span class="flow-deep-actions" role="group" aria-label="深查动作">'
                                    + "".join(actions) + "</span>")
        return lane(step_nodes("C4 补查分派", dispatch), branches)

    def closing():
        final = select("C6", "stage")
        parents = [step_node("C6 系统收尾" if s["name"] == "system_closing" else "C6 最终交付", s) for s in final]
        branches = model("C6", "最终模型")
        origins = set()
        for s in final:
            fid = s.get("output_artifact_id")
            body = payload(fid)
            if body.get("type") != "delivery_receipt":
                continue
            result = payload(body.get("detail_artifact_id")).get("result") or {}
            origin = result.get("conclusion_origin")
            origins.add(origin)
            label = {"model": "模型结论", "system": "系统收尾"}.get(origin, "交付产物")
            outcome = body.get("outcome") or {}
            note = None
            if outcome.get("result_id"):
                note = "回执登记正式结果"
            elif "result_id" in outcome and art_anchor(body.get("report_artifact_id")):
                note = "有报告，无正式结果"
            branches.append(node(label, body.get("delivery_state"), art_anchor(fid), reason=body.get("reason"), note=note))
        for origin, label in (("model", "模型结论"), ("system", "系统收尾")):
            if origin not in origins:
                branches.append(node(label))
        return lane(parents or [node("C6 最终交付")], branches)

    def saved_stage_result(code, label):
        outputs = []
        for s in select(code, "stage"):
            fid = s.get("output_artifact_id")
            result = payload(fid)
            receipt = result.get("outcome") or {}
            if files.get(fid, {}).get("kind") == "source_snapshot" and receipt.get("result_id") and "output" in result:
                note = {True: "已采用", False: "未采用"}.get(receipt.get("adopted"))
                outputs.append(node(label, "saved", art_anchor(fid), note=note))
        return outputs or [node(label)]

    kind = run.get("kind")
    items = []
    if kind == "baseline":
        fid = run.get("input_artifact_id")
        items.append(lane(step_nodes("C1 执行计划", select("C1.executor", "stage")),
                          [node("开始时保存的输入", "saved" if fid in files else "missing", art_anchor(fid))]))
        items.append(lane(step_nodes("C2 背景补充", select("C2", "stage")), backgrounds("C2", SOURCES)))
        items.append(lane(step_nodes("主分析前整理材料（C4.materials）", select("C4.materials", "stage"))))
        stages = select("C3", "stage")
        items.append(lane(step_nodes("C3 初始主分析", stages), model("C3", "主分析模型") + domain_outputs(stages)))
        items.append(routing())
        graphs = select("C5", "graph")
        outputs = []
        for s in graphs:
            gid = payload(s.get("output_artifact_id")).get("graph_artifact_id")
            if gid in files and files[gid].get("kind") == "alert_graph":
                outputs.append(node("关系图快照", "saved", art_anchor(gid)))
        items.append(lane(step_nodes("C5 构建关系图", graphs), outputs))
        reanalysis = select("C3.reanalysis", "stage")
        if reanalysis:
            items.append(lane(step_nodes("补证后再分析", reanalysis),
                              model("C3.reanalysis", "再分析模型") + domain_outputs(reanalysis)))
        else:
            items.append(lane([node("补证后再分析")]))
        items.append(closing())
    elif kind == "alert_basic":
        items.append(lane(step_nodes("A 告警分诊", select("A", "stage")), backgrounds("A", ("assets", "history", "threat_intel"))))
        items.append(lane(model("A", "分诊模型")))
        items.append(lane(saved_stage_result("A", "保存分诊结果")))
    elif kind == "incident_diagnosis":
        fid = run.get("input_artifact_id")
        input_body = payload(fid)
        members = input_body.get("members")
        recorded = input_body.get("kind") == kind and isinstance(input_body.get("parent"), dict) and isinstance(members, list)
        items.append(lane([node("读取事件和成员", "saved" if recorded else "missing", art_anchor(fid) if recorded else None,
                                note=f"{len(members)} 条成员告警" if recorded else None)]))
        items.append(lane(model("I", "模型综合分析")))
        items.append(lane(saved_stage_result("I", "保存诊断结果")))
    else:
        for s in steps:
            items.append(lane([step_node(s.get("name") or s.get("stage_code") or "步骤", s)]))
    items.append(lane([node("本轮执行", run.get("state"), run_anchor, reason=run.get("stop_reason"))],
                      [node("本轮交付", run.get("delivery_state"), run_anchor)]))
    return '<ol class="flow-lanes">' + "".join(items) + "</ol>"
