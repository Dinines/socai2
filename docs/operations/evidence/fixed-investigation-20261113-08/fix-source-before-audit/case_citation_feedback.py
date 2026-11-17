"""One diagnostic correction for complete Case replies, without changing them."""
from .analysis_review import decode, empty_reference_feedback
from .baseline_analysis_contract import time_context
from .baseline_delivery_contract import comparable_source_ids
from .case_finding_schema import conflict_errors, direct_observations
from .case_source_scope import knowledge_context

POLICY = "socai2.case-citation-correction.v9"


def feedback(content, stage, sources, members, questions, *, extra_errors=(), comparison=None):
    raw = decode(content)
    root = raw["analysis"] if stage == "C6" else raw
    # Shape/alias validation is performed by the configured output adapter.
    # Ambiguous required identities are not a local citation repair.
    for key, field, expected in (("members", "alert_id", set(members)),
                                 ("questions", "id", set(questions)),
                                 ("domains", "name", {"identity", "cloud", "phishing", "insider"})):
        ids = [row[field] for row in root[key]]
        if len(ids) != len(set(ids)) or set(ids) != expected:
            return None
    findings = {row["id"]: row for row in root["findings"]}
    if len(findings) != len(root["findings"]):
        return None
    prior = empty_reference_feedback(content, stage, sources)
    errors = prior["errors"] if prior else []
    prefix = ["analysis"] if stage == "C6" else []
    errors += [{**item, "path": prefix + item["path"]} for item in extra_errors]
    errors += [{**item, "path": prefix + item["path"]} for item in conflict_errors(root, sources)]

    def error(path, code, subject=None, **details):
        errors.append({"path": path, "code": code, "subject_id": subject, **details})

    def refs(row, field, path, scope=(), require=False, no_receipts=False, direct=False, final=False, nonempty=False):
        values, scope = row[field], set(scope)
        available = set()
        for sid in values:
            source = sources.get(sid)
            if source is None:
                error(path + [field], "source_not_in_model_input", row.get("id"), source_id=sid)
                continue
            owned = set(source["alert_ids"]) if not source.get("knowledge") else set()
            if not direct or (source["ref"]["role"] in {"observation", "human_statement"}
                              and source.get("membership_basis") != "query_binding_only"):
                available.update(owned)
            if (scope and (not final or source.get("knowledge"))
                    and not scope.intersection(owned) and not knowledge_context(source, scope)):
                error(path + [field], "source_member_mismatch", row.get("id", row.get("alert_id")),
                      source_id=sid, declared_members=sorted(scope), source_members=sorted(owned),
                      actual_role=source["ref"]["role"],
                      **{k: source[k] for k in ("membership_basis", "record_alert_ids") if k in source})
            if no_receipts and source["ref"]["role"] == "execution_receipt":
                error(path + [field], "execution_receipt_not_conclusion_evidence", source_id=sid)
        if len(values) != len(set(values)):
            error(path + [field], "duplicate_source", row.get("id"),
                  duplicate_ids=list(dict.fromkeys(sid for i, sid in enumerate(values) if sid in values[:i])))
        if nonempty and not values:
            error(path + [field], "recommendation_needs_sources", row.get("id"))
        if require and scope - available:
            details = {}
            if final:
                candidates = {}
                for member in sorted(scope - available):
                    by_role = {}
                    for sid, source in sources.items():
                        role = source["ref"]["role"]
                        if (member not in source["alert_ids"] or source.get("knowledge") or role == "execution_receipt"
                                or direct and (role not in {"observation", "human_statement"}
                                               or source.get("membership_basis") == "query_binding_only")):
                            continue
                        by_role.setdefault(role, []).append(sid)
                    candidates[member] = by_role
                details = {"declared_members": sorted(scope), "claim": row.get("text", row.get("summary")),
                           "candidate_source_ids_by_member_role": candidates}
            error(path + [field], "member_source_coverage_missing", row.get("id"),
                  uncovered_members=sorted(scope - available), direct_evidence_required=direct, **details)

    for i, row in enumerate(root["members"]):
        refs(row, "evidence_ids", prefix + ["members", i], [row["alert_id"]], row["state"] != "not_analyzed")
    for i, row in enumerate(root["questions"]):
        refs(row, "evidence_ids", prefix + ["questions", i])
    for i, row in enumerate(root["findings"]):
        path = prefix + ["findings", i]
        refs(row, "support_ids", path, row["alert_ids"], row["state"] != "unresolved")
        refs(row, "counter_ids", path, row["alert_ids"])
        overlap = sorted(set(row["support_ids"]) & set(row["counter_ids"]))
        if overlap:
            error(path + ["counter_ids"], "same_source_as_support_and_counterevidence", row["id"],
                  source_ids=overlap)
        if row["state"] == "observed":
            known = {sid: sources[sid] for sid in row["support_ids"] if sid in sources}
            observations = {sid: source for sid, source in known.items() if source["ref"]["role"] == "observation"}
            for j, sid in enumerate(row["support_ids"]):
                source = known.get(sid)
                if source is None:
                    continue
                if source["ref"]["role"] != "observation" and not time_context(source["ref"]):
                    error(path + ["support_ids", j], "non_observation_promoted_to_observed", row["id"],
                          source_id=sid, actual_role=source["ref"]["role"])
                if source.get("membership_basis") == "query_binding_only":
                    error(path + ["support_ids", j], "direct_alert_membership_not_proven", row["id"],
                          source_id=sid, query_alert_ids=source.get("query_alert_ids", []))
            if not observations:
                error(path + ["support_ids"], "observed_requires_activity_source", row["id"])
            else:
                direct = direct_observations(observations, row["alert_ids"])
                covered = {aid for source in direct.values() for aid in source["alert_ids"]}
                missing = sorted(set(row["alert_ids"]) - covered)
                if missing:
                    error(path + ["support_ids"], "observed_member_source_coverage_missing", row["id"],
                          uncovered_members=missing)
    for i, row in enumerate(root["followups"]):
        refs(row, "source_ids", prefix + ["followups", i], row["alert_ids"])
    for key in ("domains", "conflicts"):
        for i, row in enumerate(root[key]):
            path, ids = prefix + [key, i], row["finding_ids"]
            unknown = sorted(set(ids) - findings.keys())
            if unknown:
                error(path + ["finding_ids"], "unknown_local_finding", row.get("id", row.get("name")),
                      invalid_finding_ids=unknown)
            if len(ids) != len(set(ids)) or key == "conflicts" and len(set(ids)) < 2:
                error(path + ["finding_ids"], "invalid_finding_relationship", row.get("id", row.get("name")))
            if key == "domains":
                for fid in set(ids) & findings.keys():
                    if not set(row["alert_ids"]) & set(findings[fid]["alert_ids"]):
                        error(path + ["finding_ids"], "domain_finding_scope_mismatch", row["name"], finding_id=fid)
            else:
                refs(row, "evidence_ids", path)
    if stage == "C6":
        for key in ("conclusion", "impact"):
            row = raw[key]
            direct = row["state"] == "supported" if key == "conclusion" else bool(row["supported_changes"])
            refs(row, "support_ids", [key], row["alert_ids"], require=True, no_receipts=True, direct=direct, final=True)
        if "comparison" in raw:
            refs(raw["comparison"], "support_ids", ["comparison"], no_receipts=True)
            baseline_ids = comparable_source_ids(sources, comparison) if comparison is not None else set()
            if baseline_ids:
                value = raw["comparison"]
                code = "comparison_needs_selected_baseline_and_current_sources"
                if value["kind"] == "initial":
                    error(["comparison", "kind"], code, initial_not_allowed=True)
                if not value["summary"]:
                    error(["comparison", "summary"], code, nonempty_explanation_required=True)
                cited = set(value["support_ids"])
                needs_current = value["kind"] != "not_comparable"
                if not baseline_ids.intersection(cited) or needs_current and not cited - baseline_ids:
                    error(["comparison", "support_ids"], code, selected_baseline_ids=sorted(baseline_ids),
                          selected_baseline_missing=not bool(baseline_ids.intersection(cited)),
                          current_source_required=needs_current, current_source_missing=not bool(cited - baseline_ids))
            elif comparison is not None:
                if raw["comparison"]["kind"] != "not_comparable":
                    error(["comparison", "kind"], "comparison_not_available",
                          comparison_state=comparison["state"], allowed_values=["not_comparable"])
                if not raw["comparison"]["summary"]:
                    error(["comparison", "summary"], "comparison_not_available",
                          comparison_state=comparison["state"], nonempty_explanation_required=True)
        for i, row in enumerate(raw["recommendations"]):
            refs(row, "source_ids", ["recommendations", i], no_receipts=True, nonempty=True)
    if not errors:
        return None
    # The original material and complete previous answer are already in this
    # conversation. These local errors need their field values, not a second
    # full catalog of every source/finding. Other error classes keep the full
    # existing feedback; mixed errors are never hidden by this projection.
    codes = {item.get("code") for item in errors}
    comparison_instruction = ("指定旧Result没有可用比较结论，comparison.kind只能为not_comparable，summary说明不能比较的原因。"
        "当前A/I/C3/Deep判断不能替代指定旧Result，不得声称结论未变化或已修订。" if "comparison_not_available" in codes else "")
    if "comparison_needs_selected_baseline_and_current_sources" in codes:
        comparison_instruction += ("指定比较基线可用。selected_baseline_ids仅指本次选定的旧Result；同文历史背景短号、"
            "当前A/I/C3/Deep都不能替代该基线。重新阅读指定旧结论和本轮材料，核实比较种类、说明及其依据；"
            "报告变化还需本轮依据，不能只补编号而保留错误比较，也不能改成not_comparable逃避核对。")
    final_coverage = all(item.get("code") != "member_source_coverage_missing"
        or item["path"] in (["conclusion", "support_ids"], ["impact", "support_ids"]) for item in errors)
    coverage_instruction = ("最终段落的alert_ids是该段主张涉及的成员，不是自动复制全案名单。按claim、declared_members与uncovered_members核对原文及依据。"
        "candidate_source_ids_by_member_role只列缺失成员的结构合法候选，不证明其支持主张；必须回看前文事实、角色和原范围，不能只挑编号凑覆盖。"
        "没有依据时如实说明未知，并由模型据实际主张核对段落范围；不能删必要事实、编造来源或声称影响已证实。"
        if "member_source_coverage_missing" in codes and final_coverage else "")
    if (codes <= {"duplicate_source", "source_member_mismatch", "comparison_not_available", "member_source_coverage_missing",
                  "comparison_needs_selected_baseline_and_current_sources"}
            and final_coverage):
        for item in errors:
            value = raw
            for part in item["path"]:
                value = value[part]
            item["current_values"] = value
        instructions = ["仅纠正上一份完整JSON一次，返回完整JSON并接受全部校验。errors.path定位错误字段，current_values是该字段原值。"]
        if "duplicate_source" in codes:
            instructions.append("duplicate_ids中的编号在同一数组仅保留一次，不新增或替换来源。")
        if "source_member_mismatch" in codes:
            instructions.append("source_member_mismatch表示该来源不属于声明成员；按前文原始材料重新核对本条主张与范围，"
                "案件外历史不能证明本案成员事实。不能只删非法编号而保留无据断言，也不能扩大成员范围来凑引用；证据不足明确待核。")
        instructions.append(comparison_instruction)
        instructions.append(coverage_instruction)
        instructions.append("其他有效内容保持。来源与发现目录不重复列出，以前文实际输入为准，不能编造编号。")
        return {"policy": POLICY, "attempt": 1, "errors": errors,
            "allowed_sources": [], "local_findings": [], "observed_support_ids": [],
            "instruction": "".join(instructions)}
    return {"policy": POLICY, "attempt": 1, "errors": errors,
        "allowed_sources": [{"id": sid, "role": source["ref"]["role"], "alert_ids": source["alert_ids"],
                             "knowledge_reference_only": bool(source.get("knowledge")),
                             **{k: source[k] for k in ("membership_basis", "query_alert_ids", "record_alert_ids") if k in source}}
                            for sid, source in sources.items()],
        "local_findings": [{"id": fid, "alert_ids": row["alert_ids"], "direct_support_ids": sorted(direct_observations(
            {sid: sources[sid] for sid in row["support_ids"] if sid in sources}, row["alert_ids"]))} for fid, row in findings.items()],
        "observed_support_ids": sorted(direct_observations(sources, members)),
        "instruction": comparison_instruction + coverage_instruction + "仅纠正上一份完整 JSON 一次，保留独立有效内容。finding_ids 只引用本次同一 analysis.findings 中实际存在的 id，不能引用历史发现号、问题号或为过校验编造发现。按真实证据重新核对正文、状态、成员范围和引用；不得机械扩大范围、随意填号或把查询出处当记录主体。observed 只陈述直接观察支持的主张，每个涉及成员都有相应观察。标签、历史判断和人工陈述应明确归因，混合句须按主张分开表达；标签说明可留在带来源的成员摘要。knowledge_reference_only 为 true 的知识可按查询范围作辅助比较，但不能代替成员、结论或影响所需的本案来源。不能只删除非法引用而保留超出证据的断言，也不能仅改为 inferred 掩盖无据事实。可用观察编号不表示它证明该主张，须核原字段含义。没有依据应明确未解决和缺口；同一来源不能兼作支持与反证，冲突必须是两条真实发现的矛盾，缺证据不是冲突。冲突每个参与发现须有对应成员的直接 observation 支持，evidence_ids 逐 finding 覆盖这些支持且至少两个不同来源；只有回执、标签或缺口的发现不能作冲突一方。不要补凑观察编号或编造发现，缺口放限制/问题，解释差异放 alternatives，无有据矛盾用 conflicts=[]。返回完整 JSON 并接受全部校验。"}
