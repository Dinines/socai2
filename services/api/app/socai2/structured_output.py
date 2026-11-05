"""Provider shape constraints from the same contracts used on receipt.

This does not validate truth. The strict local parsers, member ownership checks,
budgets and raw-response retention remain authoritative, even if a provider
ignores these constraints. No repair call or weaker JSON-mode fallback is made.
"""
import json
import re


def compact_repeated_types(schema):
    """Factor identical text/list constraints without weakening any constraint."""
    definitions = schema["$defs"]
    for kind in ("string", "array"):
        groups = {}
        def collect(node, kind=kind, groups=groups):
            if isinstance(node, dict):
                if node.get("type") == kind and (kind == "array" or "maxLength" in node):
                    key = json.dumps(node, sort_keys=True, separators=(",", ":"))
                    groups.setdefault(key, []).append(node)
                for child in node.values():
                    collect(child)
            elif isinstance(node, list):
                for child in node:
                    collect(child)
        collect(schema)
        for index, (key, nodes) in enumerate(sorted(groups.items())):
            name = "Compact" + kind.title() + str(index)
            ref = {"$ref": "#/$defs/" + name}
            # Include both definition and reference overhead in the decision.
            if len(key) * len(nodes) <= len(key) + len(name) + 4 + len(json.dumps(ref)) * len(nodes):
                continue
            definitions[name] = json.loads(key)
            for node in nodes:
                node.clear()
                node.update(ref)


def response_format(model, sources, *, members=(), questions=(), objects=(), bindings=(), forbidden_prose=(), member_sources=None):
    schema = model.model_json_schema()
    defs = schema.setdefault("$defs", {})
    names = {"SourceId": list(sources), "AlertId": list(map(str, members)),
        "QuestionId": list(questions), "ObjectKey": list(objects), "BindingId": list(bindings)}
    if member_sources is not None:
        names["MemberSourceId"] = list(member_sources)
    for name, values in names.items():
        if values:
            defs[name] = {"type": "string", "enum": sorted(set(values))}

    arrays = {"source_ids": "SourceId", "evidence_ids": "SourceId", "support_ids": "SourceId",
        "counter_ids": "SourceId", "alert_ids": "AlertId", "object_keys": "ObjectKey"}
    if member_sources is not None:
        arrays["source_ids"] = "MemberSourceId"
    scalars = {"alert_id": "AlertId", "question_id": "QuestionId"}
    prose_fields = {"summary", "conclusion", "assessment", "statement", "explanation", "reason", "claim",
        "rationale", "limitations", "text", "evidence_requirements"}
    pattern = None
    if forbidden_prose:
        aliases = "|".join(re.escape(value) for value in sorted(set(forbidden_prose)))
        pattern = r"^(?![\s\S]*(?:^|[^A-Za-z0-9_])(?:" + aliases + r")(?![A-Za-z0-9_]))[\s\S]*$"

    def constrain_prose(node):
        if "$ref" in node:
            node = defs[node["$ref"].removeprefix("#/$defs/")]
        if node.get("type") == "array":
            constrain_prose(node["items"])
        elif node.get("type") == "string" and "enum" not in node:
            node["pattern"] = pattern

    def visit(node, name=None):
        if isinstance(node, list):
            for child in node:
                visit(child)
            return
        if not isinstance(node, dict):
            return
        # Pydantic display names/defaults add tokens but no output constraint.
        for annotation in ("title", "description", "default"):
            node.pop(annotation, None)
        for key, child in list(node.items()):
            if key == "properties":
                for field, value in child.items():
                    visit(value, field)
            else:
                visit(child)
        if pattern and name in prose_fields:
            constrain_prose(node)
        if name in arrays and node.get("type") == "array":
            target = arrays[name]
            if names[target]:
                node["items"] = {"$ref": "#/$defs/" + target}
            else:
                node["maxItems"] = 0
        if name in scalars and names[scalars[name]]:
            node.clear()
            node["$ref"] = "#/$defs/" + scalars[name]
        if name == "binding_id":
            node.clear()
            node.update({"anyOf": [{"$ref": "#/$defs/BindingId"}, {"type": "null"}]}
                if names["BindingId"] else {"type": "null"})
        if name == "members" and node.get("type") == "array" and names["AlertId"]:
            node.update(minItems=len(names["AlertId"]), maxItems=len(names["AlertId"]))

    visit(schema)
    # Analysis.Answer is a fixed Case question, unlike A's root Answer.
    answer = defs.get("Answer", {}).get("properties", {})
    if "id" in answer and "answer" in answer and names["QuestionId"]:
        answer["id"] = {"$ref": "#/$defs/QuestionId"}
    if "Domain" in defs:
        analysis = defs.get("Analysis", schema)
        analysis.get("properties", {}).get("domains", {}).update(minItems=4, maxItems=4)
    compact_repeated_types(schema)
    return {"type": "json_schema", "json_schema": {
        "name": "socai2_" + model.__name__.lower(), "strict": True, "schema": schema}}
