"""Display stored I delivery and pending review separately, without reading prose."""
REASONS = {
    "invalid_response_units_excluded": "存在未通过校验的内容，已单独排除",
    "member_analysis_missing": "部分成员缺少有效分析",
    "member_analysis_not_completed": "部分成员明确未完成分析",
    "no_valid_analysis_content": "未保留有效分析内容",
}
REVIEW = {"required": "待复核", "none_listed": "未列出待核事项", "unknown": "尚无法确认"}


def incident_fields(result):
    diagnosis = (result or {}).get("diagnosis") or {}
    delivery = diagnosis.get("delivery_assessment") or {}
    if delivery.get("schema_version") != "socai2.incident-delivery.v1":
        return []  # Historical Run delivery remains exactly as stored.
    review = delivery["review_items"]
    counts = f"成员 {len(review['unresolved_member_ids'])} 项，事件发现 {len(review['unresolved_finding_ids'])} 项，问题 {len(review['open_question_ids'])} 项"
    values = [("复核状态", REVIEW.get(review["state"], "尚无法确认")), ("待核事项", counts)]
    if delivery.get("reasons"):
        values.append(("交付说明", "；".join(REASONS.get(code, code) for code in delivery["reasons"])))
    return values


def run_delivery(run, data):
    """Read the selected subject/Run only; never infer conclusions from artifacts."""
    contracts = {"alert_basic": ("alert_assessments", "alert_id", "alerts", "latest_triage_id"),
                 "incident_diagnosis": ("incident_diagnoses", "incident_id", "incidents", "latest_diagnosis_id"),
                 "baseline": ("results", "case_id", "cases", "current_assessment_id")}
    table, subject, parents, pointer = contracts.get(run.get("kind"), (None, None, None, None))
    rows = [r for r in data.get(table, ()) if run.get(subject) is not None
            and r.get(subject) == run[subject] and r.get("source_run_id") == run["id"]
            and (not run.get("tenant_id") or r.get("tenant_id") == run["tenant_id"])]
    parent = next((p for p in data.get(parents, ()) if p.get("id") == run.get(subject)), {})
    receipts = {}
    for artifact in data.get("artifacts", ()):
        if artifact.get("run_id") != run["id"]:
            continue
        body = artifact.get("content_json") or {}
        outcome = body.get("outcome") if isinstance(body, dict) else None
        if isinstance(outcome, dict) and outcome.get("result_id"):
            receipts[outcome["result_id"]] = {"artifact_id": artifact["id"], "outcome": outcome}
    results = []
    for row in rows:
        diagnosis = row.get("diagnosis") or {}
        fields = {key: row[key] for key in ("verdict", "rationale", "confidence", "summary", "conclusion",
                  "conclusion_state", "conclusion_origin", "validation_state", "delivery_state", "state") if key in row}
        if table == "incident_diagnoses":
            fields.update({key: diagnosis[key] for key in ("conclusion", "delivery_assessment") if key in diagnosis})
        review = {key: row[key] for key in ("open_questions", "questions", "closing_note") if key in row}
        if "review_items" in (diagnosis.get("delivery_assessment") or {}):
            review["review_items"] = diagnosis["delivery_assessment"]["review_items"]
        current = {"state": "unverified", "reason": "快照缺少当前采用记录或来源关联"}
        if pointer in parent:
            current_id = parent[pointer]
            if not current_id:
                current = {"state": "not_adopted", "reason": "快照未指定当前采用"}
            elif table != "results":
                current = {"state": "adopted" if current_id == row["id"] else "not_adopted",
                           "current_result_id": current_id}
            else:
                assessment = next((a for a in data.get("case_assessments", ())
                                   if a.get("id") == current_id and a.get("case_id") == run[subject]), None)
                sources = [s for s in data.get("case_assessment_sources", ())
                           if s.get("assessment_id") == current_id and s.get("case_id") == run[subject]]
                if assessment and sources:
                    current = {"state": "adopted" if any(s.get("result_id") == row["id"] for s in sources)
                               else "not_adopted", "assessment_id": current_id, "sources": sources}
        results.append({"id": row["id"], "source_run_id": row["source_run_id"], "table": table,
                        "has_conclusion": bool(fields.get("verdict") or fields.get("conclusion")),
                        "fields": fields, "review": review, "saved_adoption": receipts.get(row["id"]),
                        "current_adoption": current})
    return {"run_id": run["id"], "results": results}
