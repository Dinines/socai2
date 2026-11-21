"""C6 closed units: immutable source spans, separate restoration and publication eligibility."""
import copy
import hashlib
from types import SimpleNamespace
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select

from . import baseline_analysis_contract as analysis
from . import baseline_delivery_contract as contract
from . import business_verdict
from . import case_c3_delivery as c3
from . import case_program_output as program
from . import severity_opinion
from .baseline_context import reference
from .baseline_delivery_compat import normalize
from .baseline_enrichment import S, error
from .baseline_model_view import blocked
from .baseline_store import F, StoreError, digest
from .case_citation_quality import normalized
from .case_followup_output import parse_final, restored_comparison
from .citation_quality import FIELDS, new_review
from .closed_json_units import read_units
from .stage_delivery import VERSION, Unit, validate_sources

RETAINED_VERSION = "socai2.case-retained-final.v1"
CONTENT_PATH = c3.CONTENT_PATH
ANALYSIS_TYPES = {**c3.TYPES, "followups": analysis.Followup}
FINAL_TYPES = {"conclusion": contract.Conclusion, "comparison": contract.Comparison,
    "impact": contract.Impact, "closing_note": contract.Text, "recommendations": contract.Recommendation}


class RetainedFinal:
    """Only received/restored fields are serialized; absent arrays iterate empty."""
    def __init__(self, fields):
        self.fields = copy.deepcopy(fields)
        self.analysis = c3.RetainedAnalysis(fields.get("analysis", {}), types=ANALYSIS_TYPES)

    def model_dump(self, **_):
        return copy.deepcopy(self.fields)

    def __getattr__(self, key):
        if key == "recommendations":
            return [contract.Recommendation.model_validate(v) for v in self.fields.get(key, [])]
        if key in FINAL_TYPES:
            value = self.fields.get(key)
            return TypeAdapter(FINAL_TYPES[key]).validate_python(value) if value is not None else None
        raise AttributeError(key)


def nonblank(value):
    if isinstance(value, str) and not value.strip():
        raise analysis.AnalysisRejected("delivery_blank_text")
    if isinstance(value, dict):
        for key, item in value.items():
            if key not in FIELDS | {"finding_ids"}:
                nonblank(item)
    elif isinstance(value, list):
        for item in value:
            nonblank(item)


def final_unit(unit, prepared, context, comparison, fixed):
    key = unit["path"].removeprefix("$.").split("[", 1)[0]
    review = new_review()
    raw = normalized(copy.deepcopy(unit["value"]), review, unit["path"])
    if blocked(raw):
        raise analysis.AnalysisRejected("unit_content_blocked")
    nonblank(raw)
    if key == "recommendations" and unit["kind"] == "empty_array":
        return [], review
    if key == "comparison" and fixed is not None:
        raise analysis.AnalysisRejected("model_must_not_supply_fixed_comparison")
    boundary = prepared["case_boundary"]
    members = {v: k for k, v in boundary["member_aliases"].items()}
    objects = {v: k for k, v in boundary["object_aliases"].items()}
    if key in {"conclusion", "impact"}:
        raw["alert_ids"] = [members[a] for a in raw["alert_ids"]]
    if key == "recommendations":
        if "id" in raw:
            raise analysis.AnalysisRejected("model_must_not_supply_recommendation_id")
        index = int(unit["path"].split("[")[1].split("]")[0])
        if index >= 12:
            raise analysis.AnalysisRejected("section_item_limit_exceeded")
        raw["id"] = "R" + str(index + 1)
        raw["object_keys"] = [objects[key] for key in raw["object_keys"]]
    item = TypeAdapter(FINAL_TYPES[key]).validate_python(raw)
    if key != "closing_note":
        fields = {name: None for name in ("conclusion", "comparison", "impact")}
        fields["recommendations"] = []
        fields[key] = [item] if key == "recommendations" else item
        contract.validate_final_units(SimpleNamespace(**fields), prepared["source_map"], context, comparison,
            citation_review=review, sections={key}, check_members=False)
        if key == "recommendations":
            c3.remap_review(review, key, unit["path"])
    return item, review


def receive(content, prepared, context, comparison, original_id, *, finish_reason="stop", original_content_path=CONTENT_PATH):
    fixed = restored_comparison(prepared, comparison)
    fields = (("analysis", "summary"), ("analysis", "conflicts_note"), *[(name,) for name in FINAL_TYPES if name != "recommendations"])
    if severity_opinion.enabled(prepared):
        fields = (*fields, ("severity_opinion",))
    if business_verdict.enabled(prepared):
        fields = (*fields, ("business_verdict",))
    arrays = (*[("analysis", name) for name in c3.SECTIONS if name != "summary"], ("recommendations",))
    scanned = read_units(content, fields=fields, arrays=arrays)
    for unit in scanned["units"]:
        start, end = unit["value_span"]
        unit.update(original_artifact_id=str(original_id), original_content_path=original_content_path,
            value_sha256=hashlib.sha256(content[start:end].encode()).hexdigest())
    analysis_scan = {**scanned,
        "units": [u for u in scanned["units"] if u["path"].startswith("$.analysis.") and c3.section(u) in c3.SECTIONS],
        "closed_sections": [p.removeprefix("$.analysis.") for p in scanned["closed_sections"]
                            if p.removeprefix("$.analysis.") in c3.SECTIONS],
        "missing_units": [u for u in scanned["missing_units"] if u["path"].startswith("$.analysis") and u["path"] != "$.analysis.conflicts_note"],
        "invalid_units": [u for u in scanned["invalid_units"] if u["path"].startswith("$.analysis")]}
    # C6 uses Analysis capacities and suggestions, not C3's executable plan limits.
    capacities = {key: next(m.max_length for m in field.metadata if hasattr(m, "max_length"))
                  for key, field in analysis.Analysis.model_fields.items() if key != "summary"}
    for unit in list(analysis_scan["units"]):
        try:
            nonblank(unit["value"])
        except analysis.AnalysisRejected as exc:
            analysis_scan["units"].remove(unit)
            analysis_scan["invalid_units"].append({"path": unit["path"], "reason_code": str(exc)})
    received = c3.admit(analysis_scan, prepared, context, None, types=ANALYSIS_TYPES,
        root_path="$.analysis", section_limits=capacities)
    retained, invalid, missing = received["retained_units"], received["invalid_units"], received["missing_units"]
    quality, derived = received["quality"], {}
    if received["analysis"]:
        derived["analysis"] = received["analysis"]
    missing += [u for u in scanned["missing_units"] if not u["path"].startswith("$.analysis")
                and not (u["path"] == "$.comparison" and fixed is not None)]
    invalid += [u for u in scanned["invalid_units"] if not u["path"].startswith("$.analysis")]
    for unit in scanned["units"]:
        if unit["path"].startswith("$.analysis."):
            if unit["path"] == "$.analysis.conflicts_note" and unit["value"] is not None:
                invalid.append({"path": unit["path"], "reason_code": "unknown_section"})
            continue
        key = unit["path"].removeprefix("$.").split("[", 1)[0]
        try:
            if key == business_verdict.FIELD:
                record = business_verdict.receive_unit(unit, content, original_id, original_content_path)
                retained.append(record)
                derived[key] = record["value"]
                continue
            if key == "severity_opinion":
                value, record, review = severity_opinion.receive_unit(
                    unit, content, prepared, original_id, original_content_path)
                retained.append(record)
                derived[key] = value
                c3.merge_review(quality, review)
                continue
            item, review = final_unit(unit, prepared, context, comparison, fixed)
            raw = unit["value"]
            ids = list(dict.fromkeys(s for k in FIELDS for s in raw.get(k, []) if isinstance(s, str))) if isinstance(raw, dict) else []
            record = Unit.model_validate({**unit,
                "declared_scope": {"alert_ids": raw["alert_ids"]} if isinstance(raw, dict) and "alert_ids" in raw else None,
                "resolved_refs": [{"source_id": sid, **{k: prepared["source_map"][sid][k] for k in ("ref", "alert_ids")}}
                    for sid in ids if sid in prepared["source_map"] and prepared["source_map"][sid]["ref"]["role"] != "execution_receipt"],
                "structure_state": "valid", "quality_issues": review["issues"]}).model_dump(mode="json")
            retained.append(record)
            c3.merge_review(quality, review)
            value = item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            if key == "recommendations":
                derived.setdefault(key, [])
                if unit["kind"] != "empty_array":
                    derived[key].append(value)
            else:
                derived[key] = value
        except (StoreError, analysis.AnalysisRejected, ValidationError, KeyError, TypeError, ValueError) as exc:
            invalid.append({"path": unit["path"], "reason_code": str(exc) if isinstance(exc, (StoreError, analysis.AnalysisRejected)) else "final_unit_shape_or_identity_invalid"})
    program_fields = []
    if program.enabled(prepared["case_boundary"]):
        program_fields += [f"$.analysis.findings[{index}].statement" for index, item in
            enumerate(derived.get("analysis", {}).get("findings", [])) if item["state"] == "observed"]
    if program.owns_coverage(prepared["case_boundary"]):
        program_fields += [f"$.analysis.questions[{index}]" for index, item in
            enumerate(derived.get("analysis", {}).get("questions", [])) if item["id"] == "coverage"]
    if fixed is not None:
        derived["comparison"] = fixed
        program_fields.append("$.comparison")
    full, adaptation = None, None
    missing_independent = any(u["path"] in {severity_opinion.PATH, business_verdict.PATH} for u in missing)
    if scanned["parse_state"] == "complete_json" and not invalid and not missing_independent:
        try:
            normalized_content, adaptation = normalize(content)
            full_review = new_review()
            full = parse_final(normalized_content, prepared, context, comparison, citation_review=full_review).model_dump(mode="json")
            # The complete validator already covers these units. Mixing its
            # dotted paths with unit-index paths would count every issue twice.
            c3.merge_review(full_review, {**new_review(), **{key: [entry for entry in quality[key]
                if entry.get("path", "").startswith(severity_opinion.PATH)] for key in ("issues", "processing", "references")}})
            quality = full_review
        except analysis.AnalysisRejected as exc:
            invalid.append({"path": "$", "reason_code": str(exc)})
    conclusion = derived.get("conclusion")
    members = {m["alert_id"]: m for m in derived.get("analysis", {}).get("members", [])}
    qualified = bool(conclusion and set(conclusion["alert_ids"]) == set(context.alerts)
        and set(members) == set(context.alerts) and all(m["state"] in {"analyzed", "unresolved"} for m in members.values()))
    accepted = full is not None or qualified
    reasons = [] if accepted else ["final_core_missing" if not conclusion else "final_whole_case_coverage_incomplete"]
    truncated = scanned["truncated"] or finish_reason == "length"
    independent_fields = {key: derived[key] for key in ("severity_opinion", business_verdict.FIELD) if key in derived}
    retained_fields = {**full, **independent_fields} if full is not None else derived
    return {"retained_output": {"schema_version": RETAINED_VERSION, "fields": retained_fields,
                "program_fields": program_fields}, "full_delivery": full, "output_adapter": adaptation,
        "retained_units": retained, "missing_units": missing, "invalid_units": invalid, "quality": quality,
        "parse": {"state": scanned["parse_state"], "truncated": truncated,
            "reasons": list(dict.fromkeys(scanned["reasons"] + (["provider_length"] if finish_reason == "length" else [])))},
        "delivery": {"state": "complete" if full is not None else "partial" if retained else "none",
            "reasons": [] if full is not None else ["final_units_missing_or_invalid", *reasons]},
        "use": {"material_paths": [u["path"] for u in retained], "dispatch_paths": [],
            "conclusion_available": bool(conclusion), "adoption_eligible": accepted, "comparison_eligible": accepted,
            "reasons": reasons + ["qualification_only_existing_adoption_and_comparison_guards_still_apply"]}}


def parser(prepared, context, comparison):
    def parse(content):
        received = receive(content, prepared, context, comparison, prepared["citation_review"]["original_response_artifact_id"],
            finish_reason=prepared.get("received_finish_reason", "stop"),
            original_content_path=prepared.get("original_content_path", CONTENT_PATH))
        prepared["c6_delivery"] = received
        c3.merge_review(prepared["citation_review"], received["quality"])
        prepared["output_adapter"] = received["output_adapter"]
        if received["full_delivery"] is not None:
            return contract.Delivery.model_validate(received["full_delivery"])
        if not received["retained_units"]:
            raise analysis.AnalysisRejected("final_output_no_usable_units")
        return RetainedFinal(received["retained_output"]["fields"])
    return parse


async def save_receipt(owner, tenant, case_id, run_id, prepared, context, comparison, model_id, response_id, reason):
    if model_id is None:
        return None
    if prepared.get("transport_stage_delivery"):
        return prepared["transport_stage_delivery"]
    async with owner.service.transaction(tenant) as store:
        run = await owner.locked(store, case_id, run_id)
        model = await store.one(select(S).where(*store.where(S, S.c.run_id == run_id, S.c.id == model_id)))
        if not model or model["state"] not in {"completed", "failed"}:
            raise StoreError("final_model_receipt_not_terminal")

        async def read(identity):
            row = await store.one(select(F).where(*store.where(F, F.c.run_id == run_id, F.c.id == UUID(str(identity)))))
            if row is None or digest(row["content_json"]) != row["sha256"]:
                raise StoreError("final_delivery_artifact_invalid")
            return row["content_json"]

        request_id = str(model["input_artifact_id"])
        originals = {request_id: await read(request_id)}
        response = await read(response_id)
        original_id = (response["payload"].get("citation_review") or {}).get("original_response_artifact_id")
        if original_id:
            original = await read(original_id)
            if original["raw"] != response["payload"].get("raw") or original["request_artifact_id"] != request_id:
                raise StoreError("final_delivery_original_mismatch")
            originals[original_id] = original
        received = prepared.get("c6_delivery")
        if received is None:
            received = receive("", prepared, context, comparison, None)
            received["parse"].update(state="unusable" if original_id else "no_response", reasons=[reason or "response_not_admitted"])
            prepared["c6_delivery"] = received
        now = await store.now()
        receipt = {"schema_version": VERSION, "type": "stage_delivery", "run_id": str(run_id),
            "step_id": str(model_id), "stage": "C6", "input_artifact_id": request_id,
            "originals": [{"artifact_id": key, "kind": "request" if key == request_id else "response", "sha256": digest(body)}
                for key, body in originals.items()],
            "execution": {"kind": "model", "call_state": model["state"], "local_state": "ended",
                "local_ended_at": model["ended_at"].isoformat(), "request_dispatched": True,
                "finish_reason": prepared.get("received_finish_reason"), "error": error(reason, now) if reason else None,
                "retry_allowed": False, "retry_reason": "C6_does_not_supplement_or_retry_output"},
            **{key: received[key] for key in ("parse", "delivery", "retained_units", "missing_units", "invalid_units", "quality", "use")}}
        if await store.one(select(S.c.id).where(*store.where(S, S.c.run_id == run_id, S.c.state == "unknown")).limit(1)):
            receipt["use"] = {**receipt["use"], "adoption_eligible": False, "comparison_eligible": False,
                "reasons": [*receipt["use"]["reasons"], "unknown_call_present"]}
        receipt = validate_sources(receipt, originals).model_dump(mode="json")
        identity = uuid4()
        await store.save_input_artifact(case_id, run_id, identity, receipt, kind="source_snapshot", schema=VERSION,
            captured_at=now, refs=[reference("artifact", key, "execution_receipt") for key in originals],
            actor_id=run["requested_by"], step_id=model_id)
        from .subject_risk_opinions import save_candidate
        await save_candidate(store, run, model_id, received)
    return {"artifact_id": str(identity), "delivery": received["delivery"],
        "missing_units": received["missing_units"], "invalid_units": received["invalid_units"]}
