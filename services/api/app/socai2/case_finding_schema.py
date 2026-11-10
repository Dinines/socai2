"""Constrain new Case finding generation without changing stored contracts."""
import copy


def direct_observations(sources, members):
    members = set(members)
    return {sid: source for sid, source in sources.items()
        if source["ref"]["role"] == "observation"
        and source.get("membership_basis") != "query_binding_only"
        and members.intersection(source["alert_ids"])}


def constrain_findings(fmt, sources, members):
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
    return fmt
