"""Replay this batch's two rejected claims through current adapters; no DB/model."""
import hashlib
import json
from pathlib import Path

from app.socai2 import case_followup_output as final
from app.socai2 import case_output_adapter as initial
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_context import Context

HERE = Path(__file__).resolve().parent
folder = HERE / "real-model-02"
database = json.loads((folder / "export/database.json").read_text())
context = Context.model_validate(next(a["content_json"] for a in database["artifacts"]
    if a["schema_version"] == "socai2.baseline-context.v1"))
base = next(a["content_json"] for a in database["artifacts"] if a["schema_version"] == "socai2.case-model-input.v1")
receipts = []
for stage, schema, call in [("C3", "socai2.baseline-analysis.v2", 1), ("C6", "socai2.baseline-delivery.v1", 5)]:
    request = next(a["content_json"]["payload"] for a in database["artifacts"]
        if a["kind"] == "model_request" and a["schema_version"] == schema)
    prepared = {**request, "coverage": base["coverage"]}
    path = folder / f"calls/call-{call}-receipt.json"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    content = json.loads(path.read_text())["raw"]["choices"][0]["message"]["content"]
    comparison = request.get("followup_boundary", {}).get("program_metadata", {}).get("comparison")
    review = initial.CaseReview(prepared, context, request["binding_map"]) if stage == "C3" else final.FinalReview(prepared, context, comparison)
    try:
        if stage == "C3":
            initial.parse(content, prepared, context, request["binding_map"])
        else:
            final.parse_final(content, prepared, context, comparison)
    except AnalysisRejected as exc:
        reason = str(exc)
    else:
        raise AssertionError("unsupported_conflicts_accepted")
    feedback = review.feedback(content)
    review.partial(content)
    retained = review.details["retained_analysis"]
    assert retained["conflicts"] == [] and retained["findings"]
    assert review.details["conclusion_adoptable"] is False
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    receipts.append({"stage": stage, "original": str(path.relative_to(HERE)), "original_sha256": before,
        "rejection": reason, "feedback": feedback["errors"], "partial_diagnostics": review.details["diagnostics"],
        "retained_findings": len(retained["findings"]), "retained_conflicts": 0, "conclusion_adoptable": False})
(HERE / "conflict-replay.json").write_text(json.dumps({"scope": "real parsers/review; recorded replies; no network/DB or edits to originals",
    "cases": receipts}, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"replayed": len(receipts), "unsupported_conflicts_rejected": True, "originals_unchanged": True}))
