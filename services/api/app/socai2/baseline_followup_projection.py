"""Join execution receipts to their immutable initial plan, never latest proposals."""
from .baseline_context import reference
from .baseline_store import StoreError


def delivery_followups(dispatch, initial):
    if dispatch is None:
        return None, []
    plan_id = dispatch["initial_analysis_artifact_id"]
    followups = (initial.get("analysis") or {}).get("followups", [])
    routes = dispatch["routes"]
    indices = [r.get("followup_index") for r in routes]
    if (any(type(i) is not int for i in indices) or len(indices) != len(followups)
            or set(indices) != set(range(len(followups)))):
        raise StoreError("followup_dispatch_plan_mismatch")
    states, candidates = [], []
    for route in sorted(routes, key=lambda r: r["followup_index"]):
        index = route["followup_index"]
        item = followups[index]
        if any(route[k] != item[k] for k in ("question_id", "mode")):
            raise StoreError("followup_dispatch_plan_mismatch")
        states.append({k: route[k] for k in ("followup_index", "state", "reason", "answer_available") if k in route})
        # Old source IDs belong to the initial request. All original text is
        # guarded before projection; required content cannot be budget-trimmed.
        candidates.append({"original": item, "required": True,
            "entry": {"role": "prior_analysis", "alert_ids": item["alert_ids"],
                "value": {"execution_plan_index": index,
                    "followup": {k: v for k, v in item.items() if k != "source_ids"}}},
            "source": {"ref": reference("artifact", plan_id, "prior_analysis", f"$.analysis.followups.{index}"),
                "alert_ids": item["alert_ids"]}})
    return {"initial_analysis_artifact_id": plan_id, "role": "execution_receipt", "routes": states}, candidates
