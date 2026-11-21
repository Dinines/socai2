"""Deep closed fields, independent answers, and immutable per-call receipts."""
import copy
import hashlib
import json
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select

from . import baseline_deep_contract as contract
from .baseline_context import reference
from .baseline_enrichment import S, error
from .baseline_store import F, StoreError, digest
from .case_c3_delivery import merge_review
from .case_citation_quality import normalized
from .citation_quality import new_review
from .closed_json_units import read_units
from .stage_delivery import VERSION, Unit, validate_sources

FIELDS = ("action", "binding_id", "reason", "answer")
CONTENT_PATH = "$.raw.choices[0].message.content"


def receive(content, prepared, original_id, *, finish_reason="stop", original_content_path=CONTENT_PATH):
    scanned = read_units(content, fields=tuple((key,) for key in FIELDS), arrays=())
    retained, values, quality = [], {}, new_review()
    invalid = copy.deepcopy(scanned["invalid_units"])
    for raw_unit in scanned["units"]:
        key = raw_unit["path"].removeprefix("$.")
        review = new_review()
        try:
            raw = normalized({key: copy.deepcopy(raw_unit["value"])}, review)[key]
            value = TypeAdapter(contract.Decision.model_fields[key].rebuild_annotation()).validate_python(raw)
            if key == "answer" and value is not None:
                contract.validate_answer(value, prepared["source_map"], citation_review=review)
            if key == "binding_id" and value is not None and value not in prepared["binding_map"]:
                raise contract.AnalysisRejected("unoffered_query_binding")
            start, end = raw_unit["value_span"]
            ids = list(dict.fromkeys(value.support_ids + value.counter_ids)) if key == "answer" and value else []
            unit = {**raw_unit, "original_artifact_id": str(original_id),
                "original_content_path": original_content_path,
                "value_sha256": hashlib.sha256(content[start:end].encode("utf-8")).hexdigest(),
                "declared_scope": None, "resolved_refs": [
                    {"source_id": sid, "ref": prepared["source_map"][sid]["ref"],
                     "alert_ids": prepared["source_map"][sid].get("alert_ids", [])}
                    for sid in ids if sid in prepared["source_map"]
                    and prepared["source_map"][sid]["ref"]["role"] != "execution_receipt"],
                "structure_state": "valid", "quality_issues": review["issues"]}
            retained.append(Unit.model_validate(unit).model_dump(mode="json"))
            values[key] = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
            merge_review(quality, review)
        except (contract.AnalysisRejected, ValidationError, KeyError, TypeError) as exc:
            invalid.append({"path": raw_unit["path"], "reason_code": str(exc)
                if isinstance(exc, contract.AnalysisRejected) else "deep_unit_shape_invalid"})
    decision = None
    if set(values) == set(FIELDS) and not invalid:
        try:
            decision = contract.parse(json.dumps({"question_id": prepared["case_boundary"]["question_id"], **values}),
                prepared["source_map"], prepared["binding_map"], prepared["case_boundary"]["question_id"],
                citation_review=quality)
        except contract.AnalysisRejected as exc:
            invalid.append({"path": "$", "reason_code": str(exc)})
    complete = decision is not None and scanned["parse_state"] == "complete_json" and not scanned["missing_units"]
    reasons = list(scanned["reasons"])
    if finish_reason == "length":
        reasons.append("provider_length")
    return {"decision": decision, "answer": values.get("answer"), "retained_units": retained,
        "missing_units": scanned["missing_units"], "invalid_units": invalid, "quality": quality,
        "parse": {"state": scanned["parse_state"], "truncated": scanned["truncated"] or finish_reason == "length",
            "reasons": list(dict.fromkeys(reasons))},
        "delivery": {"state": "complete" if complete else "partial" if retained else "none",
            "reasons": [] if complete else ["deep_decision_incomplete_or_invalid"]},
        "use": {"material_paths": [u["path"] for u in retained],
            "dispatch_paths": [u["path"] for u in retained] if decision and decision.action == "query" else [],
            "conclusion_available": False, "adoption_eligible": False, "comparison_eligible": False,
            "reasons": ["Deep_final_conclusion_and_adoption_not_applicable"]}}


def parser(prepared):
    def parse(content):
        review = prepared["citation_review"]
        received = receive(content, prepared, review["original_response_artifact_id"],
            finish_reason=prepared.get("received_finish_reason", "stop"),
            original_content_path=prepared.get("original_content_path", CONTENT_PATH))
        prepared["unit_delivery"] = received
        merge_review(review, received["quality"])
        if received["decision"] is None:
            raise contract.AnalysisRejected("deep_decision_incomplete_or_invalid")
        return received["decision"]
    return parse


async def save_receipt(owner, tenant, case_id, run_id, prepared, model_id, response_id, reason):
    if model_id is None:
        return None
    if prepared.get("transport_stage_delivery"):
        return prepared["transport_stage_delivery"]
    async with owner.service.transaction(tenant) as store:
        run = await owner.locked(store, case_id, run_id)
        model = await store.one(select(S).where(*store.where(S, S.c.run_id == run_id, S.c.id == model_id)))
        if not model or model["state"] not in {"completed", "failed"}:
            raise StoreError("deep_model_receipt_not_terminal")

        async def read(identity):
            row = await store.one(select(F).where(*store.where(F, F.c.run_id == run_id, F.c.id == UUID(str(identity)))))
            if row is None or digest(row["content_json"]) != row["sha256"]:
                raise StoreError("deep_delivery_artifact_invalid")
            return row["content_json"]

        request_id = str(model["input_artifact_id"])
        originals = {request_id: await read(request_id)}
        response = await read(response_id)
        original_id = (response["payload"].get("citation_review") or {}).get("original_response_artifact_id")
        if original_id:
            original = await read(original_id)
            if original["raw"] != response["payload"].get("raw") or original["request_artifact_id"] != request_id:
                raise StoreError("deep_delivery_original_mismatch")
            originals[original_id] = original
        received = prepared.get("unit_delivery")
        if received is None:
            received = receive("", prepared, None)
            received["parse"].update(state="unusable" if original_id else "no_response", reasons=[reason or "response_not_admitted"])
        now = await store.now()
        receipt = {"schema_version": VERSION, "type": "stage_delivery", "run_id": str(run_id),
            "step_id": str(model_id), "stage": "C4.deep", "input_artifact_id": request_id,
            "originals": [{"artifact_id": identity, "kind": "request" if identity == request_id else "response",
                           "sha256": digest(body)} for identity, body in originals.items()],
            "execution": {"kind": "model", "call_state": model["state"], "local_state": "ended",
                "local_ended_at": model["ended_at"].isoformat(), "request_dispatched": True,
                "finish_reason": prepared.get("received_finish_reason"), "error": error(reason, now) if reason else None,
                "retry_allowed": False, "retry_reason": "Deep_does_not_supplement_or_retry_output"},
            **{key: received[key] for key in ("parse", "delivery", "retained_units", "missing_units", "invalid_units", "quality", "use")}}
        receipt = validate_sources(receipt, originals).model_dump(mode="json")
        identity = uuid4()
        await store.save_input_artifact(case_id, run_id, identity, receipt, kind="source_snapshot", schema=VERSION,
            captured_at=now, refs=[reference("artifact", i, "execution_receipt") for i in originals],
            actor_id=run["requested_by"], step_id=model_id)
    return {"artifact_id": str(identity), "delivery": received["delivery"],
        "missing_units": received["missing_units"], "invalid_units": received["invalid_units"]}
