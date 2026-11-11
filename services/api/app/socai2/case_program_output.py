"""Program-owned Case facts; original model replies and historical boundaries stay intact."""
import json
from collections import Counter

from pydantic import TypeAdapter, ValidationError

from .baseline_analysis_contract import AnalysisRejected, Text

VERSION = "socai2.case-program-output.v1"
PENDING = "原始观察尚未通过装配校验。"


def enabled(boundary):
    return boundary.get("program_output") == VERSION


def observation_literals(records, aliases):
    result, groups = {}, {}
    for row in records:
        ref = row["ref"]
        if ref["role"] != "observation" or row.get("membership_basis") == "query_binding_only":
            continue
        members = tuple(aliases.get(str(a), "范围未明") for a in row["alert_ids"])
        key = (ref["type"], str(ref["id"]), tuple(ref.get("row_keys") or []), row.get("record_key"), members)
        if key not in groups:
            groups[key] = len(groups) + 1
        value = row.get("original_value", row["value"])
        result[row["id"]] = {"group": f"{'、'.join(members) or '共同范围'}/原记录{groups[key]}",
            "path": ref.get("source_path") or "$", "value": value}
    return result


def observed_text(finding, boundary):
    literals = boundary["observation_literals"]
    parts = []
    for sid in finding["support_ids"]:
        if sid not in literals:
            raise AnalysisRejected("observed_original_field_unavailable")
        row = literals[sid]
        value = json.dumps(row["value"], ensure_ascii=False, separators=(",", ":"))
        parts.append(f"[{row['group']}｜{sid}] {row['path']}={value}")
    text = "\n".join(parts)
    try:
        TypeAdapter(Text).validate_python(text)
    except ValidationError:
        raise AnalysisRejected("observed_original_fields_exceed_statement_contract") from None
    return text


def restore_observed(root, boundary):
    if not enabled(boundary):
        return
    for finding in root["findings"]:
        if finding["state"] != "observed":
            continue
        if "statement" in finding:
            raise AnalysisRejected("observed_statement_is_program_owned")
        try:
            finding["statement"] = observed_text(finding, boundary)
        except AnalysisRejected:
            # A typed placeholder only enables the existing per-unit review.
            # validate_program rejects it; it can never be adopted as a fact.
            finding["statement"] = PENDING


def program_errors(root, boundary):
    if not enabled(boundary):
        return []
    errors = []
    for i, finding in enumerate(root["findings"]):
        if finding["state"] == "observed":
            try:
                observed_text(finding, boundary)
            except AnalysisRejected as exc:
                errors.append({"path": ["findings", i, "support_ids"], "code": str(exc),
                    "subject_id": finding["id"], "reason": "原字段不可得或超出既有文字容量；选取本发现必需的原字段，不能删掉必要事实、编造内容或换状态掩盖错误。"})
    return errors


def validate_program(root, boundary):
    errors = program_errors(root, boundary)
    if errors:
        raise AnalysisRejected(errors[0]["code"])
    if enabled(boundary):
        for finding in root["findings"]:
            if finding["state"] == "observed" and finding["statement"] != observed_text(finding, boundary):
                raise AnalysisRejected("observed_program_text_mismatch")


def coverage_question(root, boundary):
    data = boundary["coverage_facts"]
    member_states = Counter(row["state"] for row in root["members"])
    question_states = Counter(row["state"] for row in root["questions"] if row["id"] != "coverage")
    read_states = Counter(row.get("state", "unrecorded") for row in data.get("material_reads", {}).values())
    if not read_states:
        read_states["unrecorded"] = data["total_members"]
    parts = [f"程序记录：材料视图涉及{data['visible_members']}/{data['total_members']}个成员，省略项{data['omission_count']}。",
        "材料读取回执：" + "，".join(f"{state}={count}" for state, count in read_states.items())
        + "（available 仅为所选字段可读取；无回执为 unrecorded；逐成员限制与遗漏见所引材料回执）。",
        "模型分析状态：" + "，".join(f"{state}={member_states.get(state, 0)}" for state in ("analyzed", "unresolved", "not_analyzed")) + "。",
        f"其余业务问题未决{question_states.get('unresolved', 0)}项；矛盾条目{len(root['conflicts'])}项；后续需求{len(root['followups'])}项（内容见对应条目）。"]
    refs = list(data.get("material_source_ids", []))
    for row in data["queries"]:
        parts.append("；".join(f"{k}={json.dumps(v, ensure_ascii=False, separators=(',', ':'))}" for k, v in row.items() if k != "source_ids"))
        refs.extend(row["source_ids"])
    if not data["queries"]:
        parts.append("本次输入未记录可核对的查询回执；不能推定已查、查空或成功。")
    if data["execution_states"]:
        parts.append("补查执行记录：" + json.dumps(data["execution_states"], ensure_ascii=False, separators=(",", ":")))
    answer = "\n".join(parts)
    try:
        TypeAdapter(Text).validate_python(answer)
    except ValidationError:
        raise AnalysisRejected("program_coverage_exceeds_statement_contract") from None
    return {"id": "coverage", "state": "answered" if refs else "unresolved", "answer": answer,
        "evidence_ids": list(dict.fromkeys(refs)), "limitations": [
            "以上是输入覆盖与所保存分析状态，不代表已读原件全文、正文已核实或调查已完成。",
            "业务未知仍见相应问题、成员、矛盾和后续条目；查空不证明安全，未查/失败/未知不作查空。"]}


def restore_coverage(root, boundary):
    if not enabled(boundary) or "coverage_facts" not in boundary:
        return
    if any(row["id"] == "coverage" for row in root["questions"]):
        raise AnalysisRejected("coverage_question_is_program_owned")
    root["questions"].append(coverage_question(root, boundary))
