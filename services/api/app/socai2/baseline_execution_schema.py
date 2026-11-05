"""C3-only binding constraints and equivalent provider definition aliases."""
from copy import deepcopy
from string import ascii_letters


def execution_format(response_format, bindings):
    """Constrain query selectors without changing the canonical response DTO."""
    output = deepcopy(response_format)
    schema = output["json_schema"]["schema"]
    definitions = schema["$defs"]
    original = definitions["ExecutionFollowup"]

    def resolved(value):
        if "$ref" in value:
            value = definitions[value["$ref"].removeprefix("#/$defs/")]
        return deepcopy(value)

    groups = {}
    for alias, binding in bindings.items():
        members = tuple(sorted(set(binding["alert_ids"])))
        objects = tuple(sorted({obj["object_key"] for obj in binding["objects"]}))
        if not members:
            raise ValueError("execution_binding_members_empty")
        groups.setdefault((members, objects), []).append(alias)
    branches = []
    for (members, objects), aliases in sorted(groups.items()):
        query = deepcopy(original)
        props = query["properties"]
        props["mode"] = {"type": "string", "enum": ["query"]}
        props["binding_id"] = ({"$ref": "#/$defs/BindingId"} if set(aliases) == set(bindings)
            else {"type": "string", "enum": sorted(aliases)})
        members_shape = resolved(props["alert_ids"])
        if (not set(members) <= set(definitions["AlertId"]["enum"])
                or len(members) > members_shape["maxItems"]
                or not set(objects) <= set(definitions.get("ObjectKey", {}).get("enum", []))):
            raise ValueError("execution_binding_outside_canonical_scope")
        members_shape.update(minItems=len(members), maxItems=len(members), uniqueItems=True)
        members_shape["items"] = ({"$ref": "#/$defs/AlertId"}
            if set(members) == set(definitions["AlertId"]["enum"])
            else {"type": "string", "enum": list(members)})
        props["alert_ids"] = members_shape
        objects_shape = resolved(props["object_keys"])
        if objects:
            objects_shape["items"] = {"type": "string", "enum": list(objects)}
        else:
            objects_shape["maxItems"] = 0
        props["object_keys"] = objects_shape
        branches.append(query)
    other = deepcopy(original)
    other["properties"]["mode"]["enum"] = [m for m in other["properties"]["mode"]["enum"] if m != "query"]
    other["properties"]["binding_id"] = {"type": "null"}
    branches.append(other)
    if len(branches) > 1:
        # Share the identical enum, not field values or executable scopes.
        name = "ExecutionPriority"
        if name in definitions:
            raise ValueError("execution_priority_definition_collision")
        definitions[name] = deepcopy(original["properties"]["priority"])
        for branch in branches:
            branch["properties"]["priority"] = {"$ref": "#/$defs/" + name}
        definitions["ExecutionFollowup"] = {"anyOf": branches}
    else:
        definitions["ExecutionFollowup"] = other
    return output


def compact_definitions(schema):
    """Rename root definitions and matching refs only; reject unsafe graphs.

    Call after provider transformations, which may need semantic definition
    names. Output fields, enum strings and all validation constraints are kept.
    C3 has no recursive types; a recursive/missing/external ref is a hard error.
    """
    definitions = schema.get("$defs", {})
    aliases = {name: ascii_letters[i] if i < len(ascii_letters) else "d" + str(i)
        for i, name in enumerate(sorted(definitions))}

    def ref_name(value):
        if not isinstance(value, str) or not value.startswith("#/$defs/"):
            raise ValueError("execution_schema_ref_not_local")
        raw = value.removeprefix("#/$defs/")
        if "/" in raw or "~" in raw.replace("~0", "").replace("~1", ""):
            raise ValueError("execution_schema_ref_not_definition")
        name = raw.replace("~1", "/").replace("~0", "~")
        if name not in definitions:
            raise ValueError("execution_schema_ref_missing")
        return name

    def references(node):
        found = set()
        if isinstance(node, dict):
            if "$ref" in node:
                found.add(ref_name(node["$ref"]))
            if "$defs" in node:
                raise ValueError("execution_schema_nested_definitions")
            for value in node.values():
                found.update(references(value))
        elif isinstance(node, list):
            for value in node:
                found.update(references(value))
        return found

    graph = {name: references(value) for name, value in definitions.items()}
    references({key: value for key, value in schema.items() if key != "$defs"})
    visited = set()

    def check(name, active):
        if name in active:
            raise ValueError("execution_schema_ref_cycle")
        if name in visited:
            return
        for child in graph[name]:
            check(child, active | {name})
        visited.add(name)
    for name in graph:
        check(name, set())

    def rewrite(node):
        if isinstance(node, dict):
            return {key: "#/$defs/" + aliases[ref_name(value)] if key == "$ref" else rewrite(value)
                for key, value in node.items()}
        if isinstance(node, list):
            return [rewrite(value) for value in node]
        return node
    output = rewrite(schema)
    output["$defs"] = {aliases[name]: value for name, value in output["$defs"].items()}
    return output


def compact_execution_wire(body):
    """Apply only to a new C3 execution request, after prepare_request."""
    output = deepcopy(body)
    fmt = output["text"]["format"] if "text" in output else output["response_format"]["json_schema"]
    fmt["schema"] = compact_definitions(fmt["schema"])
    return output
