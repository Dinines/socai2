"""Offline diagnostics of immutable m1 answers. Counterfactuals never get adopted."""
import copy
import json
import re
from pathlib import Path

from app.socai2 import baseline_analysis_contract
from app.socai2.answer_validation import Checks
from app.socai2.baseline_context import Context
from app.socai2.model_input_view import items

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/operations/evidence/socai2-model-comparison-20261104/m1"


def parse_c(answer, packet):
    try:
        baseline_analysis_contract.parse(json.dumps(answer, ensure_ascii=False), packet["source_map"],
            Context.model_validate(packet["context"]), packet["coverage"])
        return {"accepted_by_parser": True}
    except baseline_analysis_contract.AnalysisRejected as exc:
        return {"accepted_by_parser": False, "error": str(exc)}


def main():
    bundle = json.loads((OUT / "plan-and-packets.json").read_text("utf-8"))
    parsed = json.loads((OUT / "parsed-results.json").read_text("utf-8"))
    packets = {p["id"]: p for p in bundle["packets"]}
    rows = {r["cell"]: r for r in parsed["cells"]}
    output = {"new_model_calls": 0, "business_adoption": False, "original_answer_modified": False}
    output["A_current_inline_reference_mismatch"] = {}
    for label in ("A0", "A1"):
        answer = rows[label + "-current-deepseek"]["answer"]
        packet = packets[label + "-current"]
        mentioned = set(re.findall(r"(?<![A-Za-z0-9_])S[1-9][0-9]*(?![A-Za-z0-9_])", answer["rationale"]))
        missing = mentioned - set(answer["evidence_ids"])
        visible = {i["id"]: i for i in items(packet["data"])}
        output["A_current_inline_reference_mismatch"][label] = {
            sid: {"role": packet["source_map"][sid]["ref"]["role"], "path": visible[sid]["field"],
                "value": visible[sid]["value"]} for sid in sorted(missing)}

    packet, original = packets["C3-current"], rows["C3-current-deepseek"]["answer"]
    output["C3_source_role_failures"] = [{"finding": f["id"], "state": f["state"],
        "non_observation_support": {sid: packet["source_map"][sid]["ref"] for sid in f["support_ids"]
            if packet["source_map"][sid]["ref"]["role"] != "observation"}}
        for f in original["findings"] if f["state"] == "observed"]
    temporary = copy.deepcopy(original)
    for finding in temporary["findings"]:
        if finding["state"] == "observed":
            finding["support_ids"] = [sid for sid in finding["support_ids"]
                if packet["source_map"][sid]["ref"]["role"] == "observation"]
    output["C3_diagnostic_counterfactual_remove_time_refs_only"] = parse_c(temporary, packet)
    for domain in temporary["domains"]:
        if domain["applicability"] != "applicable":
            domain["finding_ids"] = []
    output["C3_diagnostic_counterfactual_also_remove_undetermined_domain_links"] = parse_c(temporary, packet)
    assert original == rows["C3-current-deepseek"]["answer"]

    packet = packets["I-current"]
    prior = [i for i in items(packet["data"]) if i["role"] == "prior_analysis"]
    output["I_prior_rationale_contains_unscoped_old_aliases"] = [{"id": i["id"],
        "aliases": sorted(set(re.findall(r"S[1-9][0-9]*", json.dumps(i["value"]))))} for i in prior]
    current = {i["id"]: i for i in items(packet["data"])}
    output["I_alias_collision_example"] = {"prior_item": "S20", "old_alias_S14_meant": "prior_A_history_query",
        "current_S14_means": current["S14"]["field"], "current_S14_value": current["S14"]["value"]}
    checks = Checks()
    # Diagnostic only: S1 is a reference to the other member's process. A prior
    # rationale containing literal S1 currently exempts it from prose checking.
    checks.prose("Reference S1", "$.diagnostic", [], packet["source_map"], packet["data"], "incident_answer")
    output["I_prior_alias_triggers_literal_exemption_observation"] = {
        "provided_structured_refs": [], "text": "Reference S1", "diagnostics": checks.entries,
        "expected_for_nonliteral_citation": "unbound citation should be reported", "business_output": False}
    output["C3_source_states_as_sent"] = packets["C3-current"]["data"]["source_states"]
    with (OUT / "offline-diagnostics.json").open("x", encoding="utf-8") as stream:
        json.dump(output, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
