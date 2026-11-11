"""Keep independent valid analysis units; never repair a model's factual prose.

The strict parser remains authoritative. Each retained unit is checked inside a
neutral complete contract, then the combined subset is checked again. Original
answers are stored separately; placeholders describe validation, not evidence.
"""
import copy
import json

from pydantic import ValidationError

from . import baseline_analysis_contract as contract
from .baseline_model_view import blocked
from .baseline_store import digest

POLICY = "socai2.analysis-review.v1.2"
NOTE = "该项引用未通过校验，原答保留，结论待核。"


def decode(content):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise contract.AnalysisRejected("duplicate_json_key")
            out[key] = value
        return out
    def invalid(_):
        raise contract.AnalysisRejected("invalid_json_number")
    try:
        value = json.loads(content, object_pairs_hook=unique, parse_constant=invalid)
    except (ValueError, TypeError) as exc:
        if isinstance(exc, contract.AnalysisRejected):
            raise
        raise contract.AnalysisRejected("analysis_shape_invalid") from None
    if not isinstance(value, dict) or blocked(value):
        raise contract.AnalysisRejected("analysis_shape_or_output_guard_invalid")
    return value


def partial_analysis(content, sources, context, coverage, *, bindings=None, validator=None):
    raw = decode(content)
    model = contract.Analysis if bindings is None else contract.ExecutionAnalysis
    try:
        model.model_validate(raw)
    except ValidationError:
        raise contract.AnalysisRejected("analysis_shape_invalid") from None
    # Missing/ambiguous subject identities are not a local citation problem.
    for key, field, expected in (("members", "alert_id", set(context.alerts)),
            ("questions", "id", {q.id for q in context.questions}), ("domains", "name", set(contract.DOMAINS))):
        ids = [item[field] for item in raw[key]]
        if len(ids) != len(set(ids)) or set(ids) != expected:
            raise contract.AnalysisRejected("analysis_required_identity_invalid")
    if len({f["id"] for f in raw["findings"]}) != len(raw["findings"]):
        raise contract.AnalysisRejected("duplicate_finding")
    def checked(value):
        parsed = contract.parse(json.dumps(value, ensure_ascii=False), sources, context, coverage, bindings=bindings)
        if validator is not None:
            validator(value)
        return parsed
    try:
        return checked(raw), []
    except contract.AnalysisRejected:
        pass
    neutral = {"summary": "保留通过引用校验的分析片段；部分内容待核。",
        "members": [{"alert_id": m["alert_id"], "state": "not_analyzed", "summary": NOTE,
            "evidence_ids": [], "limitations": [NOTE]} for m in raw["members"]],
        "questions": [{"id": q["id"], "state": "unresolved", "answer": NOTE,
            "evidence_ids": [], "limitations": [NOTE]} for q in raw["questions"]],
        "domains": [{"name": d["name"], "applicability": "undetermined", "reason": NOTE,
            "alert_ids": [], "finding_ids": [], "limitations": [NOTE]} for d in raw["domains"]],
        "findings": [], "conflicts": [], "followups": []}
    checked(neutral)
    result, diagnostics = copy.deepcopy(neutral), []
    for key in ("members", "questions", "findings", "domains", "conflicts", "followups"):
        for index, item in enumerate(raw[key]):
            candidate = copy.deepcopy(neutral)
            # Domain/conflict references depend on retained findings, never on
            # a dropped finding with the same original identifier.
            if key in {"domains", "conflicts"}:
                candidate["findings"] = copy.deepcopy(result["findings"])
            if key in {"members", "questions", "domains"}:
                candidate[key][index] = item
            else:
                candidate[key] = [item]
            try:
                checked(candidate)
            except contract.AnalysisRejected as exc:
                diagnostics.append({"path": [key, index], "code": str(exc), "action": "exclude_dependent_claim",
                    "original_sha256": digest(item)})
                continue
            if key in {"members", "questions", "domains"}:
                result[key][index] = copy.deepcopy(item)
            else:
                result[key].append(copy.deepcopy(item))
    # Cross-item constraints (e.g. duplicate conflict IDs) remain fail-closed.
    return checked(result), diagnostics


def empty_reference_feedback(content, stage, sources):
    raw = decode(content)
    root = raw.get("analysis") if stage == "C6" else raw
    if not isinstance(root, dict):
        return None
    prefix, errors = (["analysis"] if stage == "C6" else []), []
    for collection, state, states, field in (
        ("questions", "state", {"answered"}, "evidence_ids"),
        ("members", "state", {"analyzed"}, "evidence_ids"),
        ("findings", "state", {"observed", "inferred"}, "support_ids")):
        collection_value = root.get(collection, [])
        if not isinstance(collection_value, list):
            continue
        for index, item in enumerate(collection_value):
            if isinstance(item, dict) and isinstance(item.get(state), str) and item[state] in states and item.get(field) == []:
                errors.append({"path": [*prefix, collection, index, field], "subject_id": item.get("id", item.get("alert_id")),
                    "reason": "该状态表示已有依据，但引用列表为空。"})
    if not errors:
        return None
    return {"policy": POLICY, "attempt": 1, "errors": errors,
        "allowed_sources": [{"id": sid, "role": source["ref"]["role"], "alert_ids": source["alert_ids"]}
            for sid, source in sources.items()],
        "instruction": "纠正上一份完整 JSON 一次。仅引用本次输入中真实支持该项的已有来源；无充分来源时改为未解决/未分析并说明缺口，不能随意填编号。保留其他有效内容，返回完整 JSON，仍须通过全部校验。"}


class Review:
    def __init__(self, stage, sources, context, coverage, *, bindings=None, validator=None):
        self.stage, self.sources, self.context, self.coverage, self.bindings = stage, sources, context, coverage, bindings
        self.details = None
        self.validator = validator

    def feedback(self, content):
        return empty_reference_feedback(content, self.stage, self.sources)

    def partial(self, content):
        raw = decode(content)
        root = raw.get("analysis") if self.stage == "C6" else raw
        value, diagnostics = partial_analysis(json.dumps(root), self.sources, self.context, self.coverage,
                                              bindings=self.bindings, validator=self.validator)
        self.details = {"policy": POLICY, "state": "partial", "diagnostics": diagnostics,
            "retained_analysis": value.model_dump(mode="json"),
            "conclusion_adoptable": False, "reason": "invalid_units_or_final_conclusion_excluded",
            "limitations": ["source_identity_and_scope_checks_do_not_prove_prose_true",
                "free_text_summary_dependencies_unknown_summary_not_reused",
                "invalid_final_delivery_never_adopts_overall_conclusion"]}
        # C3 can continue planning with valid units. C6 publishes this subset
        # separately, without turning a rejected conclusion into needs_review.
        return value if self.stage == "C3" else None
