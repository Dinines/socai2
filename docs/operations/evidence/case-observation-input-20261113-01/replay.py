"""Six saved answers, two program versions; no model, network or database."""
import copy
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text())
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / CONFIG["policy"])
sys.path.insert(0, str(ROOT / "services/api"))

from app.socai2 import case_followup_output as final
from app.socai2 import case_output_adapter as initial
from app.socai2 import case_program_output as program
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_context import Context
from app.socai2.baseline_delivery_compat import normalize
from app.socai2.baseline_store import encoded
from app.socai2.runtime_policy import active_policy


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    path = HERE / "offline" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    body = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        assert path.read_text() == body, "immutable_evidence_differs:" + str(path)
    else:
        with path.open("x") as file:
            file.write(body)


source = ROOT / CONFIG["offline_source"]
old_hashes = {str(p.relative_to(ROOT)): sha(p) for p in source.rglob("*") if p.is_file()}
profile = active_policy().case_io
roots = profile.business["render"]["event_roots"]
outcomes = []
for key, numbers in CONFIG["offline_cases"].items():
    folder = source / key
    summary = read(folder / "summary.json")
    db = read(folder / "export/database.json")
    artifacts = [a for a in db["artifacts"] if a["run_id"] == summary["run_id"]]
    base = next(a["content_json"] for a in artifacts if a["schema_version"] == "socai2.case-model-input.v1")
    context = Context.model_validate(next(a["content_json"] for a in artifacts
                                         if a["schema_version"] == "socai2.baseline-context.v1"))
    for number in numbers:
        call = next(c for c in summary["calls"] if c["number"] == number)
        artifact = next(a for a in artifacts if a["id"] == call["request_artifact_id"])
        request = artifact["content_json"]["payload"]
        response = next(a["content_json"]["payload"] for a in artifacts
                        if a["step_id"] == artifact["step_id"] and a["kind"] == "model_response")
        body = read(folder / call["request_file"])["body"]
        raw = read(folder / call["reply_file"])["raw"]
        assert body == request["body"] and raw == response["raw"]
        content, _ = normalize(raw["choices"][0]["message"]["content"]) if call["stage"] == "C6" else (
            raw["choices"][0]["message"]["content"], None)
        prepared = copy.deepcopy({**base, **request, "coverage": base["coverage"], "messages": body["messages"]})
        if call["stage"] == "C6":
            for aid, coverage in prepared["coverage"].items():
                coverage["included"] = sum(aid in r["alert_ids"] for r in prepared["followup_boundary"]["records"])
        original = copy.deepcopy(prepared)
        comparison = summary["comparison"]

        def parse(value, stage=call["stage"], content=content, context=context,
                  request=request, comparison=comparison):
            if stage == "C3":
                return initial.parse(content, value, context, request.get("binding_map", {}))
            return final.parse_final(content, value, context, comparison)

        def rejection(value, parse=parse):
            try:
                parse(value)
            except AnalysisRejected as exc:
                return str(exc)
            return None

        old_error = rejection(prepared)
        assert old_error == call["validation_error"]
        prefix = f"{key}-call-{number:02}-{call['stage']}"
        detail = {"scenario": key, "call": number, "stage": call["stage"], "old_rejection": old_error,
                  "original_request": str((folder / call["request_file"]).relative_to(ROOT)),
                  "original_answer": str((folder / call["answer_file"]).relative_to(ROOT))}
        if call["stage"] == "C3":
            boundary = prepared["case_boundary"]
            old_literals = copy.deepcopy(boundary["observation_literals"])
            literals = program.observation_literals(base["input_ledger"]["records"], boundary["member_aliases"], event_roots=roots)
            assert {sid: {k: row[k] for k in ("group", "path", "value")} for sid, row in literals.items()} == old_literals
            boundary.update(program_output=program.VERSION, observation_literals=literals)
            answer = json.loads(content)
            finding = next(f for f in answer["findings"] if f["state"] == "observed")
            old_text = "\n".join(f"[{old_literals[sid]['group']}｜{sid}] {old_literals[sid]['path']}="
                + json.dumps(old_literals[sid]["value"], ensure_ascii=False, separators=(",", ":")) for sid in finding["support_ids"])
            new_text = program.observed_text(finding, boundary)
            assert all(sid in new_text for sid in finding["support_ids"])
            assert prepared["source_map"] == original["source_map"] and prepared["messages"] == original["messages"]
            save(prefix + "-observation-before.txt", old_text)
            save(prefix + "-observation-after.txt", new_text)
            save(prefix + "-literal-map.json", literals)
            new_error = rejection(prepared)
            assert new_error == ("source_member_mismatch" if number == 1 else None)
            if new_error is None:
                save(prefix + "-assembled-preview.json", parse(prepared).model_dump(mode="json"))
            detail.update(new_rejection=new_error, old_characters=len(old_text), new_characters=len(new_text),
                          selected_source_ids=finding["support_ids"], original_fields_and_sources_unchanged=True,
                          boundary_version_preview=program.VERSION, historical_run_unchanged=True)
        else:
            feedback = final.FinalReview(prepared, context, comparison).feedback(content)
            assert len(feedback["errors"]) == 1 and feedback["allowed_sources"] == feedback["local_findings"] == []
            error = feedback["errors"][0]
            assert error["path"] == ["impact", "support_ids"] and error["code"] == "member_source_coverage_missing"
            assert error["uncovered_members"] == (["A2"] if key == "B01" else ["A1", "A2", "A3"])
            assert original == prepared
            review = final.FinalReview(prepared, context, comparison)
            assert review.partial(content) is None and review.details["conclusion_adoptable"] is False
            save(prefix + "-feedback.json", feedback)
            save(prefix + "-correction-messages-preview.json", {"kind": "offline_not_dispatched",
                "messages": body["messages"] + [{"role": "assistant", "content": content},
                                                {"role": "user", "content": encoded(feedback).decode()}]})
            # For the final original attempt this is diagnostic only, not a proposal for a second correction.
            previous = response.get("correction_feedback")
            detail.update(new_rejection=rejection(prepared), old_feedback_characters=len(encoded(previous).decode()) if previous else None,
                          new_feedback_characters=len(encoded(feedback).decode()), original_fields_and_sources_unchanged=True,
                          diagnostic_only_after_original_correction=number == numbers[-1], conclusion_adoptable=False)
        outcomes.append(detail)
assert all(sha(ROOT / name) == digest for name, digest in old_hashes.items())
save("summary.json", {"kind": "six_saved_answer_offline_comparison", "status": "passed", "real_model_calls": 0,
    "database_calls": 0, "network_calls": 0, "original_files_sha256": old_hashes,
    "profile_identity": profile.identity, "outcomes": outcomes,
    "limits": ["C3_v2_is_an_explicit_offline_boundary_preview_not_a_saved_Run_change",
               "new_C6_feedback_not_sent_to_model", "no_final_quality_or_adoption_claim"]})
print(json.dumps(outcomes, ensure_ascii=False))
