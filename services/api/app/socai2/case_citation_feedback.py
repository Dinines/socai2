"""One diagnostic correction for complete Case replies, without changing them."""
from .analysis_review import decode, empty_reference_feedback

POLICY = "socai2.case-citation-correction.v1"


def feedback(content, stage, sources, members, questions):
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
        "local_findings": [{"id": fid, "alert_ids": row["alert_ids"]} for fid, row in findings.items()],
        "instruction": "仅纠正上一份完整 JSON 一次，保留独立有效内容。finding_ids 只引用本次同一 analysis.findings 中实际存在的 id，不能引用历史发现号、问题号或为过校验编造发现。按真实证据重新核对成员范围和引用；不得机械扩大范围、随意填号或把查询出处当记录主体。没有依据应明确未解决和缺口；冲突必须是两条真实发现的矛盾，缺证据不是冲突。返回完整 JSON 并接受全部校验。"}
