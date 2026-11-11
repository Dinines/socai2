"""One diagnostic correction for complete Case replies, without changing them."""
from .analysis_review import decode, empty_reference_feedback
from .baseline_analysis_contract import time_context
from .case_finding_schema import conflict_errors, direct_observations

POLICY = "socai2.case-citation-correction.v3"


def feedback(content, stage, sources, members, questions, *, extra_errors=()):
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

    def refs(row, field, path, scope=(), require=False, no_receipts=False, direct=False, final=False):
        values, scope = row[field], set(scope)
        available = set()
        for sid in values:
            source = sources.get(sid)
            if source is None:
                error(path + [field], "source_not_in_model_input", row.get("id"), source_id=sid)
                continue
            owned = set(source["alert_ids"])
            if not direct or (source["ref"]["role"] in {"observation", "human_statement"}
                              and source.get("membership_basis") != "query_binding_only"):
                available.update(owned)
            if scope and not final and not scope.intersection(owned):
                error(path + [field], "source_member_mismatch", row.get("id", row.get("alert_id")),
                      source_id=sid, declared_members=sorted(scope), source_members=sorted(owned))
            if no_receipts and source["ref"]["role"] == "execution_receipt":
                error(path + [field], "execution_receipt_not_conclusion_evidence", source_id=sid)
        if len(values) != len(set(values)):
            error(path + [field], "duplicate_source", row.get("id"))
        if require and (values or final) and scope - available:
            error(path + [field], "member_source_coverage_missing", row.get("id"),
                  uncovered_members=sorted(scope - available), direct_evidence_required=direct)

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
        for i, row in enumerate(raw["recommendations"]):
            refs(row, "source_ids", ["recommendations", i], no_receipts=True)
    if not errors:
        return None
    return {"policy": POLICY, "attempt": 1, "errors": errors,
        "allowed_sources": [{"id": sid, "role": source["ref"]["role"], "alert_ids": source["alert_ids"],
                             **{k: source[k] for k in ("membership_basis", "query_alert_ids", "record_alert_ids") if k in source}}
                            for sid, source in sources.items()],
        "local_findings": [{"id": fid, "alert_ids": row["alert_ids"], "direct_support_ids": sorted(direct_observations(
            {sid: sources[sid] for sid in row["support_ids"] if sid in sources}, row["alert_ids"]))} for fid, row in findings.items()],
        "observed_support_ids": sorted(direct_observations(sources, members)),
        "instruction": "仅纠正上一份完整 JSON 一次，保留独立有效内容。finding_ids 只引用本次同一 analysis.findings 中实际存在的 id，不能引用历史发现号、问题号或为过校验编造发现。按真实证据重新核对正文、状态、成员范围和引用；不得机械扩大范围、随意填号或把查询出处当记录主体。observed 只陈述直接观察支持的主张，每个涉及成员都有相应观察。标签、历史判断和人工陈述应明确归因，混合句须按主张分开表达；标签说明可留在带来源的成员摘要。不能只删除非法引用而保留超出证据的断言，也不能仅改为 inferred 掩盖无据事实。可用观察编号不表示它证明该主张，须核原字段含义。没有依据应明确未解决和缺口；同一来源不能兼作支持与反证，冲突必须是两条真实发现的矛盾，缺证据不是冲突。冲突每个参与发现须有对应成员的直接 observation 支持，evidence_ids 逐 finding 覆盖这些支持且至少两个不同来源；只有回执、标签或缺口的发现不能作冲突一方。不要补凑观察编号或编造发现，缺口放限制/问题，解释差异放 alternatives，无有据矛盾用 conflicts=[]。返回完整 JSON 并接受全部校验。"}
