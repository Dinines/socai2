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
