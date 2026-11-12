"""Build only C3's configured text input; downstream legacy views remain separate."""
import copy

from pydantic_core import to_jsonable_python

from . import baseline_analysis_contract as contract
from . import baseline_model_view as legacy
from . import knowledge_model_input as knowledge
from .baseline_context import reference
from .baseline_store import StoreError, encoded
from .case_input_hierarchy import render_tools
from .case_input_text import prepare
from .case_query_snapshot import source as query_source
from .case_source_scope import query_scope
from .incident_model_boundary import query_items, query_record_identity
from .model_input_view import source_members
from .program_facts import case_facts
from .runtime_policy import active_policy, draft_limit

SCHEMA = "socai2.case-model-input.v1"


def selected_profile(context):
    profile = active_policy().case_io
    if profile is None or context.case_input_profile != profile.identity:
        raise StoreError("case_input_profile_changed", 422)
    return profile


def build(context, context_id, enrichment, states, materials, *, execution_time=None, run_id=None, _excluded_knowledge=()):
    profile = selected_profile(context)
    frozen = context.model_dump(mode="json")
    paired = query_source(frozen)
    if not paired:
        raise StoreError("case_query_snapshot_missing", 422)
    context_id = str(context_id)
    material_values = to_jsonable_python(materials)
    data = {"items": [], "program_facts": case_facts(context, context_id, materials,
        execution_time=execution_time, run_id=run_id)}
    source_map, rejected = {}, []
    # Full selected background candidates, without passing through the old
    # scalar/byte clipping. Inspect originals before the business projection.
    for index, item in enumerate(legacy.candidates(context, context_id, [], None)):
        ref = item["ref"]
        path = ref.get("source_path") or ""
        if (path.startswith("$.alerts.") and path.rsplit(".", 1)[-1] in {"alert", "triage", "material"}
                or path.startswith("$.incidents.") and path.endswith(".diagnosis")):
            continue
        if legacy.blocked(item["original"]):
            rejected.append({"source": ref, "reason": "input_guard", "required": item["required"]})
            continue
        data["items"].append({"source": ref, "value": item["value"], "limitations": item["limitations"]})
        source_map[str(index)] = {"ref": ref, "alert_ids": source_members(context, ref, {})}
    additional, tool_payloads = [], {str(identity): body for identity, body, _ in enrichment}
    for identity, body, _ in enrichment:
        owners = sorted(set(body.get("actual_args", {}).get("scope", {}).get("alert_ids", [])) & set(context.alerts))
        for ref, original, projected, _ in query_items(None, {"id": str(identity), "content_json": body}, profile.business["render"]):
            if body.get("tool_name") == "knowledge" and (ref.get("source_path") or "").startswith("$.rows."):
                # Ranking and index identity remain in the original receipt/4177,
                # not as apparent evidence strength in the model's business view.
                for key in ("similarity", "content_sha256"):
                    projected.pop(key, None)
            query_members = source_members(context, ref, tool_payloads) if ref["source_path"] else owners
            additional.append({"ref": ref, "original_value": original, "value": projected,
                "query_record_identity": query_record_identity(body, ref["source_path"]),
                **query_scope(body, ref["source_path"], query_members, context.alerts),
                **knowledge.metadata(body, ref),
                "block": "background_query"})
    additional, knowledge_omissions = knowledge.coalesce(additional)
    additional, excluded = knowledge.choose(additional, "C3", context.alerts, profile.config["knowledge_selection"],
                                            excluded=_excluded_knowledge)
    knowledge_omissions.extend(excluded)
    sample = {"context": frozen, "context_id": context_id, "materials": material_values,
        "data": data, "request": {"source_map": source_map}, "query_source": paired,
        "additional_queries": additional}
    prepared = prepare(sample, profile.config, profile.business)
    # Model references resolve to this Run's frozen C1 copy. Original A artifact
    # identity/path is retained in the ledger, never fetched as a latest value.
    copied = {row["id"]: f"$.alerts.{aid}.queries.{index}.content_json"
              for aid, item in frozen["alerts"].items() for index, row in enumerate(item["queries"])}
    for row in prepared["records"]:
        original = row["ref"]
        if original["type"] == "artifact" and original["id"] in copied:
            row["original_reference"] = copy.deepcopy(original)
            path = copied[original["id"]] + (original["source_path"] or "$")[1:]
            row["ref"] = reference("artifact", context_id, original["role"], path)
            prepared["source_map"][row["id"]]["ref"] = row["ref"]
        if (row["ref"]["type"] == "artifact" and row["ref"]["id"] == context_id
                and context.citation_roles.get(row["ref"]["source_path"]) != row["ref"]["role"]):
            raise StoreError("case_input_source_role_unregistered", 422)
    prepared["query_supplement_was_in_original_c1"] = True
    prepared["omissions"].extend(rejected + knowledge_omissions)
    if rejected:
        prepared["user"] += "\n部分背景原文被输入检查排除；不能视作完整材料。"
    output = profile.config["c3_output"]
    from .case_program_output import observation_literals
    system = legacy.SYSTEM + "\n" + "\n".join(line for line in contract.PROMPT.splitlines()
        if not line.startswith(("followups只提需求", "仅返回符合response_format"))) + "\n" + contract.EXECUTION_PROMPT + "\n" + profile.config["system_suffix"]
    for replacement in profile.config["system_replacements"]:
        system = system.replace(replacement["old"], replacement["new"])
    system += "\n" + profile.config["citation_instruction"]
    system += "\n" + output["instruction"].replace("{max_followups}", str(output["max_followups"]))
    system += "\n" + profile.config["program_output"]["instruction"]
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prepared["user"]}]
    optional = [r["knowledge"]["identity"] for r in prepared["records"] if r.get("knowledge")]
    if len(encoded(messages)) > draft_limit() and optional:
        return build(context, context_id, enrichment, states, materials, execution_time=execution_time, run_id=run_id,
                     _excluded_knowledge=(*_excluded_knowledge, optional[-1]))
    reason = ("required_model_input_unavailable" if any(r["required"] for r in rejected) else
              "case_input_exceeds_prepared_limit" if len(encoded(messages)) > draft_limit() else
              "projected_message_guard_blocked" if any(legacy.blocked_message(m["content"]) for m in messages) else None)
    prepared.pop("query_supplement")
    return {"schema_version": SCHEMA, "ready": reason is None, "reason": reason,
        "messages": messages if reason is None else [], "source_map": prepared["source_map"],
        "coverage": prepared["coverage"], "omissions": prepared["omissions"],
        "source_state_ledger": states, "case_boundary": {"profile": profile.identity, "max_followups": output["max_followups"],
            "program_output": profile.config["program_output"]["version"],
            "observation_literals": observation_literals(prepared["records"], prepared["member_aliases"]),
            "member_aliases": prepared["member_aliases"], "object_aliases": prepared["object_aliases"]},
        "input_ledger": prepared, "bytes": len(encoded(messages)),
        "limitations": ["structured_sources_and_frozen_query_copies_not_a_full_raw_review",
            "input_presence_does_not_prove_model_analysis"]}


def messages(prepared, context, options):
    from .baseline_tool_catalog import data
    from .case_output_adapter import alias_catalog

    profile = selected_profile(context)
    if prepared["case_boundary"]["profile"] != profile.identity:
        raise StoreError("case_input_profile_changed", 422)
    output = copy.deepcopy(prepared["messages"])
    catalog = data(options or [])
    if legacy.blocked(catalog):
        raise StoreError("analysis_input_contract_or_size", 422)
    visible_catalog = alias_catalog(catalog, prepared["case_boundary"])
    visible_catalog["capabilities"] = [c for c in visible_catalog["capabilities"] if c["available"]]
    presentation = (render_tools(visible_catalog, profile.config) if options else
                    {"text": "[可用调查工具｜程序提供]\n本轮无可用查询候选。", "ledger": [],
                     "catalog": visible_catalog, "capabilities": []})
    presentation["original_catalog"] = catalog
    prepared["tool_presentation"] = presentation
    output.append({"role": "user", "content": presentation["text"]})
    if len(encoded(output)) > draft_limit() or any(legacy.blocked(m["content"]) for m in output):
        raise StoreError("analysis_input_contract_or_size", 422)
    return output, prepared["source_map"]
