"""Resolve aliases once and render the same C6 publication into a report."""
import html
import re

from .baseline_contracts import Publication


def make_publication(value, context, members, prepared, comparison, graph, operation_key, reason):
    source_map = prepared.get("source_map", {})
    def refs(ids):
        return [source_map[i]["ref"] for i in ids]

    def scope(ids):
        result = context.scope.model_dump(mode="json")
        # This output contract claims member scope, not every object occurring
        # anywhere in the Case. Object-specific targets belong to recommendations.
        result.update(kind="selected_alerts", alert_ids=list(map(str, ids)), object_keys=[])
        return result

    limitations = []
    if prepared.get("omissions"):
        limitations.append("final_model_input_omitted_fields")
    if context.omissions:
        limitations.append("frozen_context_has_omissions")
    if graph["delivery_state"] != "complete":
        limitations.append("source_graph_partial_external_topology_not_queried")
    background = prepared.get("source_states", [])
    if not background or any(s["outcome"] not in {"data", "empty", "not_applicable"} or s["truncated"] for s in background):
        limitations.append("background_source_coverage_incomplete")
    findings, questions, deliveries, recommendations = [], [], [], []
    if value:
        analysis = value.analysis
        if any(m.state != "analyzed" for m in analysis.members):
            limitations.append("members_unresolved_or_not_analyzed")
        if any(q.state == "unresolved" for q in analysis.questions) or analysis.followups:
            limitations.append("open_questions_or_followups")
        if any(d.applicability == "undetermined" for d in analysis.domains):
            limitations.append("domain_applicability_undetermined")
        if any(c.state == "unresolved" for c in analysis.conflicts):
            limitations.append("unresolved_conflicts")
        for item in analysis.findings:
            findings.append({"id": item.id, "state": item.state, "statement": item.statement,
                "scope": scope(item.alert_ids), "support": refs(item.support_ids), "counterevidence": refs(item.counter_ids),
                "limitations": item.limitations + ["替代解释：" + a for a in item.alternatives]})
        question_map = {q.id: q for q in context.questions}
        for item in analysis.questions:
            q = question_map[item.id].model_dump(mode="json")
            q.update(state="answered" if item.state in {"answered", "not_applicable"} else "unresolved",
                answer=item.answer, evidence_refs=refs(item.evidence_ids), limitations=item.limitations + (
                    ["source_analysis_question_not_applicable"] if item.state == "not_applicable" else []))
            questions.append(q)
        covered = set(value.conclusion.alert_ids)
        for item in analysis.members:
            deliveries.append({"alert_id": item.alert_id, "read_state": members[item.alert_id]["read_state"],
                "assessment_state": item.state, "conclusion_covered": item.alert_id in covered,
                "assessment": item.summary, "limitations": "；".join(item.limitations + limitations) or None,
                "evidence_refs": refs(item.evidence_ids)})
        for item in value.recommendations:
            recommendations.append({"id": item.id, "action_type": item.action_type,
                "targets": [{"object_key": k, "display_name": k} for k in item.object_keys], "reason": item.reason,
                "approval_requirement": "unknown", "source_refs": refs(item.source_ids),
                "limitations": item.limitations + ["recommendation_only_no_approval_or_execution"]})
        impact = {"summary": value.impact.summary, "supported_changes": value.impact.supported_changes,
            "cannot_generalize": value.impact.cannot_generalize, "affected_scope": scope(value.impact.alert_ids),
            "next_steps": value.impact.next_steps}
    else:
        limitations.append("no_accepted_final_model_conclusion")
        for aid, row in sorted(members.items(), key=lambda pair: str(pair[0])):
            deliveries.append({"alert_id": aid, "read_state": row["read_state"],
                "assessment_state": row["analysis_state"], "conclusion_covered": False, "assessment": None,
                "limitations": "没有有效最终结论；既有步骤及中间分析保留。", "evidence_refs": []})
        questions = [q.model_copy(update={"state": "not_attempted", "limitations": [
            "final_synthesis_not_accepted_prior_question_answers_remain_in_artifacts"]}).model_dump(mode="json") for q in context.questions]
        impact = {"summary": None, "supported_changes": [], "cannot_generalize": ["没有有效最终模型结论，不能确认案件影响"],
            "affected_scope": scope([]), "next_steps": ["核对停止原因与已保存材料后，由用户决定后续调查"]}
    result = Publication.model_validate({"operation_key": operation_key,
        "terminal_state": "completed" if value else "failed", "stop_reason": "final_delivery_saved" if value else reason,
        "stop_detail": None, "title": "基础调查结果" if value else "基础调查系统交接",
        "conclusion": value.conclusion.text if value else None,
        "conclusion_state": value.conclusion.state if value else "unavailable",
        "conclusion_origin": "model" if value else "system", "validation_state": "accepted" if value else "system_only",
        "closing_note": value.closing_note if value else "本轮未形成可采用的模型结论；执行材料和中间分析已保留，需后续跟进。",
        "findings": findings, "questions": questions, "recommendations": recommendations,
        "change_kind": value.comparison.kind if value else "initial" if comparison["state"] == "initial" else "not_comparable",
        "change_summary": value.comparison.summary if value else None if comparison["state"] == "initial" else "未形成有效最终结论，未进行判断比较。",
        "case_impact": impact, "graph_artifact_id": graph["graph_artifact_id"], "report_artifact_id": None,
        "delivery_state": "partial" if limitations or not value else "complete", "members": deliveries})
    return result, limitations


def markdown(report):
    """No second model write. Escaping prevents source text becoming HTML/links."""
    def esc(value):
        return re.sub(r"([\\`*{}\[\]()!#_>|])", r"\\\1", html.escape(str(value), quote=False)).replace("\r", "")

    data = report["result"]
    lines = ["# " + esc(data["title"]), "", "结论来源：" + esc(data["conclusion_origin"]),
        "交付状态：" + esc(data["delivery_state"]), "", "## 本轮保留结论", "",
        esc(data["conclusion"] or "未形成有效模型结论"), "", esc(data["closing_note"]),
        "", "## 比较与案件影响", "", "变化类型：" + esc(data["change_kind"]),
        esc(data["change_summary"] or "无指定比较基线。"),
        esc(data["case_impact"]["summary"] or "案件影响未确认。")]
    lines += ["", "不能推广："] + ["- " + esc(s) for s in data["case_impact"]["cannot_generalize"]]
    lines += ["", "有依据的影响："] + ["- " + esc(s) for s in data["case_impact"]["supported_changes"]]
    lines += ["", "后续工作："] + ["- " + esc(s) for s in data["case_impact"]["next_steps"]]
    lines += ["", "比较范围变化：", "新增成员：" + esc(", ".join(report["comparison"]["added_alert_ids"]) or "无"),
        "移出成员：" + esc(", ".join(report["comparison"]["removed_alert_ids"]) or "无")]
    lines += ["", "## 成员覆盖", ""]
    for member in data["members"]:
        lines += ["- " + esc(member["alert_id"]) + "：" + esc(member["assessment_state"]) +
            "；纳入结论=" + str(member["conclusion_covered"]), "  " + esc(member["assessment"] or "无最终逐成员判断"),
            "  " + esc(member["limitations"] or "无额外限制")]
    for label, key, text_key in [("发现", "findings", "statement"), ("问题", "questions", "answer"),
            ("建议（未执行）", "recommendations", "reason")]:
        lines += ["", "## " + label, ""]
        for item in data[key]:
            lines += ["- " + esc(item["id"]) + "：" + esc(item[text_key] or "未记录")]
            for role in ("support", "counterevidence", "evidence_refs", "source_refs"):
                if item.get(role):
                    lines += ["  " + role + "：" + esc("; ".join(r["id"] + (r["source_path"] or "") for r in item[role]))]
            lines += ["  " + esc(s) for s in item["limitations"]]
    if report["delivery"]:
        lines += ["", "结论限制："] + ["- " + esc(s) for s in report["delivery"]["conclusion"]["limitations"]]
        lines += ["", "## 领域与矛盾", ""]
        for domain in report["delivery"]["analysis"]["domains"]:
            lines += ["- " + esc(domain["name"] + ": " + domain["applicability"] + "；" + domain["reason"])]
        for conflict in report["delivery"]["analysis"]["conflicts"]:
            lines += ["- " + esc(conflict["id"] + ": " + conflict["state"] + "；" + conflict["explanation"])]
    lines += ["", "## 执行用量", "", "模型调用：" + str(report["execution"]["model_calls"]),
        "Tool调用：" + str(report["execution"]["tool_calls"]), "Token总量：" + (
            str(report["execution"]["total_tokens"]) if report["execution"]["total_tokens"] is not None else "未知")]
    lines += ["", "## 来源与限制", "", "图工件：" + esc(data["graph_artifact_id"]),
        "比较结果：" + esc(report["comparison"]["result_id"] or "无"),
        "来源别名对应本次模型实际可见字段；派生图与旧分析不作为独立证据。"]
    for sid, source in report["source_map"].items():
        ref = source["ref"]
        lines += ["- " + esc(sid) + "：" + esc(ref["type"] + "/" + ref["id"]) + " " +
            esc(ref["source_path"] or "") + "（" + esc(ref["role"]) + "）"]
    lines += ["- " + esc(item) for item in report["limitations"]]
    return "\n".join(lines) + "\n"
