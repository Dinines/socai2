"""Task-specific followup views; select structure, never summarize prose."""
import copy

from .baseline_store import encoded
from .case_c3_input_selection import select_rows
from .case_input_hierarchy import project

REFERENCE_KEYS = {"evidence_ids", "source_ids", "support_ids", "counter_ids"}


def prior(analysis, question, lead, prior_id, config, ledger, *, program_owned):
    selected = copy.deepcopy(analysis)
    policy = config["followup_input_selection"]
    if question:
        allowed = set(map(str, question.scope.alert_ids))
        selected = {
            "question": next(q for q in selected["questions"] if q["id"] == question.id),
            "findings": [f for f in selected.get("findings", [])
                         if not f.get("alert_ids") or allowed.intersection(map(str, f["alert_ids"]))],
            "followups": [f for f in selected["followups"] if f["question_id"] == question.id],
        }
    else:
        if program_owned:
            selected["questions"] = [q for q in selected["questions"] if q["id"] != "coverage"]
        plans = [r for r in lead if str(r["source"]["ref"]["id"]) == str(prior_id)
                 and "execution_plan_index" in r["entry"]["value"]]
        if plans and [r["original"] for r in plans] == analysis["followups"]:
            selected.pop("followups")  # The same immutable plan is shown once below.
    return project(selected, "prior", policy, ledger, "selected_C3")


def references(value, mapping):
    """Only walk typed prior analyses/answers, never guess refs in free text."""
    result = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in REFERENCE_KEYS:
                result.extend(mapping[s]["ref"] for s in child if s in mapping)
            else:
                result.extend(references(child, mapping))
    elif isinstance(value, list):
        for child in value:
            result.extend(references(child, mapping))
    return result


def records(base, context, config, business, required, omissions):
    # These are the already guarded frozen business records, not raw envelopes.
    # Share only structural selection with C3; question/prior selection is above.
    rows = copy.deepcopy(base["input_ledger"]["records"])
    frozen_refs = {r["id"]: copy.deepcopy(r["ref"]) for r in rows}
    original_refs = {encoded(r["ref"]): r["original_reference"] for r in rows if r.get("original_reference")}
    # C3 seals A-query references into C1 paths after selecting fields. Undo
    # that path wrapping only for the shared selector, then restore exact refs.
    for row in rows:
        row["ref"] = copy.deepcopy(row.get("original_reference", row["ref"]))
    start = len(omissions)
    selected = select_rows(rows, context.model_dump(mode="json"), config, business["render"], omissions,
                           required_refs=[original_refs.get(encoded(ref), ref) for ref in required])
    for row in selected:
        row["ref"] = frozen_refs[row["id"]]
    for item in omissions[start:]:
        if item.get("source_id") in frozen_refs and "ref" in item:
            item["ref"] = frozen_refs[item["source_id"]]
    return selected


def available_tools(catalog):
    catalog = copy.deepcopy(catalog)
    catalog["capabilities"] = [c for c in catalog["capabilities"] if c["available"]]
    return catalog
