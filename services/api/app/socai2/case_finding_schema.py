"""Constrain new Case finding generation without changing stored contracts."""
import copy

from .baseline_analysis_contract import AnalysisRejected


def direct_observations(sources, members):
    members = set(members)
    return {sid: source for sid, source in sources.items()
        if source["ref"]["role"] == "observation"
        and source.get("membership_basis") != "query_binding_only"
        and members.intersection(source["alert_ids"])}


def conflict_errors(root, sources):
    """Check original support, not whether two natural-language claims contradict."""
    findings = {row["id"]: row for row in root["findings"]}
    errors = []
    for i, conflict in enumerate(root["conflicts"]):
        selected = set(conflict["evidence_ids"])
        allowed = set()
        for fid in conflict["finding_ids"]:
            finding = findings.get(fid)
            if finding is None:  # Existing contract reports unknown identities.
                continue
            members = set(finding["alert_ids"])
            original = direct_observations({sid: sources[sid] for sid in finding["support_ids"] if sid in sources}, members)
            allowed.update(original)
            covered = {aid for sid, source in original.items() if sid in selected for aid in source["alert_ids"]}
            if members - covered:
                errors.append({"path": ["conflicts", i, "evidence_ids"], "code": "conflict_original_support_missing",
                    "subject_id": conflict["id"], "finding_id": fid, "uncovered_members": sorted(members - covered),
                    "allowed_support_ids": sorted(original)})
        if len(selected) < 2 or selected - allowed:
            errors.append({"path": ["conflicts", i, "evidence_ids"], "code": "conflict_requires_original_observations",
                "subject_id": conflict["id"], "invalid_source_ids": sorted(selected - allowed)})
    return errors


def validate_conflicts(root, sources):
    errors = conflict_errors(root, sources)
    if errors:
        raise AnalysisRejected(errors[0]["code"])


def constrain_findings(fmt, sources, members, *, program_owned=False):
    schema = fmt["json_schema"]["schema"]
    definitions = schema["$defs"]
    finding = definitions["Finding"]
    observations = direct_observations(sources, members)

    def variant(state, field, source_ids=None):
        # Providers compile branches independently: preserve every field and
        # limit in each branch, including compact shared array constraints.
        result = copy.deepcopy(finding)
        props = result["properties"]
        props["state"] = {"type": "string", "enum": [state]}
        if state == "observed" and program_owned:
            props.pop("statement")
            result["required"].remove("statement")
        array = props[field]
        while "$ref" in array:
            array = definitions[array["$ref"].removeprefix("#/$defs/")]
        array = copy.deepcopy(array)
        array["minItems"] = 1
        if source_ids is not None:
            array["items"] = {"type": "string", "enum": sorted(source_ids)}
        props[field] = array
        return result

    branches = []
    if observations:
        branches.append(variant("observed", "support_ids", observations))
    if sources:
        branches.append(variant("inferred", "support_ids"))
    branches.append(variant("unresolved", "limitations"))
    definitions["Finding"] = {"anyOf": branches}
    conflict = definitions["Conflict"]["properties"]
    array = conflict["evidence_ids"]
    while "$ref" in array:
        array = definitions[array["$ref"].removeprefix("#/$defs/")]
    array = copy.deepcopy(array)
    if len(observations) >= 2:
        array.update(items={"type": "string", "enum": sorted(observations)}, minItems=2, uniqueItems=True)
    else:
        array["maxItems"] = 0
        analysis = schema if "conflicts" in schema["properties"] else definitions["Analysis"]
        analysis["properties"]["conflicts"]["maxItems"] = 0
    conflict["evidence_ids"] = array
    return fmt
