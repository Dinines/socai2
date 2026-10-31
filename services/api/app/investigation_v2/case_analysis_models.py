"""Chat-completions calls preserving the tool-call protocol's visible fields."""
from copy import deepcopy
import httpx

from app.core.airgap import enforce_airgap_for_url
from app.services import llm_health
from app.services.llm_safety import validate_messages
from app.services.model_aliases import at_bundled_gateway, completions_url_for_base

MAX_OUTPUT_TOKENS = 3000
FINISH_TOOL = {"type": "function", "function": {
    "name": "finish_analysis", "description": "已有材料足以形成有边界的报告时结束补查；仍有缺口可在报告说明。此操作不查询数据。",
    "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}}


def alert_references(context):
    return {item["evidence_id"]: item["data"]["alert_id"] for item in context["evidence"]
            if item.get("kind") == "alert"}


def model_member_context(view):
    """Use current A references in model scope; keep original UUIDs in the ledger."""
    view = deepcopy(view)
    reverse = {value: key for key, value in alert_references(view).items()}
    for name in ("all_member", "selected_member", "read_member"):
        values = view.pop(name + "_ids", None)
        if values is not None:
            view[name + "_refs"] = [reverse[value] for value in values if value in reverse]
            if name == "selected_member":
                view["unreadable_member_count"] = sum(value not in reverse for value in values)
    for item in view["evidence"]:
        if item.get("kind") == "alert":
            # Product Tool source_alert_id still needs this exact source UUID.
            item["data"]["alert_ref"] = item["evidence_id"]
    return view


class ReportContractError(ValueError):
    def __init__(self, errors):
        super().__init__(";".join(dict.fromkeys(error["type"] for error in errors)))
        self.errors = errors


def translate_report(report, context, evidence):
    """Map explicit current A references to public UUID fields, without adding citations."""
    if not isinstance(report, dict):
        raise ReportContractError([{"location": [], "type": "object_required"}])
    report = deepcopy(report)
    refs = alert_references(context)
    known = {item["evidence_id"] for item in evidence}
    errors, assessed = [], []
    for section in ("member_assessments", "relationships", "open_questions"):
        items = report.get(section, [])
        if not isinstance(items, list):
            continue  # Pydantic reports field type errors after translation.
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            single = section == "member_assessments"
            field = "alert_ref" if single else "alert_refs"
            original = item.pop(field, None)
            members = [original] if single else original
            location = [section, index, field]
            if not isinstance(members, list) or any(not isinstance(ref, str) or ref not in refs for ref in members):
                errors.append({"location": location, "type": "unknown_member_reference", "allowed": list(refs)})
                continue
            members = list(dict.fromkeys(members))
            if section == "relationships" and len(members) < 2:
                errors.append({"location": location, "type": "two_distinct_members_required"})
            if single:
                if members[0] in assessed:
                    errors.append({"location": location, "type": "duplicate_member_assessment"})
                assessed += members
            citations = item.get("evidence_ids")
            if isinstance(citations, list) and all(isinstance(ref, str) for ref in citations):
                item["evidence_ids"] = list(dict.fromkeys(citations))
                if set(citations) - known:
                    errors.append({"location": [section, index, "evidence_ids"],
                                   "type": "unknown_evidence_reference", "allowed": sorted(known)})
                if section != "open_questions" and set(members) - set(citations):
                    errors.append({"location": [section, index, "evidence_ids"],
                                   "type": "missing_member_source_reference", "required": members})
            # Reject public UUID fields in model output instead of silently overwriting them.
            public = "alert_id" if single else "alert_ids"
            if public in item:
                errors.append({"location": [section, index, public], "type": "use_alert_ref_fields"})
            item[public] = refs[members[0]] if single else [refs[ref] for ref in members]
    if set(assessed) != set(refs):
        errors.append({"location": ["member_assessments"], "type": "cover_each_readable_member_once", "required": list(refs)})
    if errors:
        raise ReportContractError(errors)
    return report


def conclusion_format(schema: dict, evidence_ids: list[str], member_ids: list[str], read_member_ids=None):
    def strict(value):
        if isinstance(value, list):
            return [strict(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: strict(item) for key, item in value.items() if key not in {"default", "title"}}
        if result.get("type") == "object":
            result.update(additionalProperties=False, required=list(result.get("properties", {})))
        return result

    output = strict(schema)
    readable = member_ids if read_member_ids is None else read_member_ids
    output["properties"]["member_assessments"].update(minItems=len(readable), maxItems=len(readable))
    for definition in output.get("$defs", {}).values():
        properties = definition.get("properties", {})
        if "evidence_ids" in properties and evidence_ids:
            properties["evidence_ids"]["items"]["enum"] = evidence_ids
        if "alert_id" in properties:
            properties["alert_ref"] = {"type": "string", "enum": readable or member_ids}
            del properties["alert_id"]
            definition["required"] = ["alert_ref" if key == "alert_id" else key for key in definition["required"]]
        if "alert_ids" in properties:
            properties["alert_refs"] = properties.pop("alert_ids")
            properties["alert_refs"]["items"] = {"type": "string", "enum": member_ids}
            properties["alert_refs"]["maxItems"] = len(member_ids)
            definition["required"] = ["alert_refs" if key == "alert_ids" else key for key in definition["required"]]
            if len(member_ids) < 2 and properties["alert_refs"].get("minItems") == 2:
                output["properties"]["relationships"]["maxItems"] = 0
    return {"type": "json_schema", "json_schema": {
        "name": "case_analysis_conclusion", "strict": True, "schema": output}}


async def call_model(config, messages: list[dict], tools: list[dict], *, timeout_seconds: float,
                     response_format=None, tool_choice=None):
    # The shared validator checks content, but its returned normalization
    # omits tool_calls/tool_call_id. Keep those protocol fields explicitly.
    validate_messages(messages)
    visible = [{key: value for key, value in message.items()
                if key in {"role", "content", "tool_calls", "tool_call_id"}} for message in messages]
    url = completions_url_for_base(config.base_url)
    enforce_airgap_for_url(url)
    body = {"model": config.model, "messages": visible, "max_tokens": MAX_OUTPUT_TOKENS}
    if tools:
        body["tools"] = tools
    if response_format is not None:
        body["response_format"] = response_format
    if tool_choice is not None:
        body["tool_choice"] = tool_choice
    if timeout_seconds <= 0:
        raise TimeoutError("case_analysis_deadline_elapsed")
    # LiteLLM consumes this routing option; direct/BYOK providers may reject it.
    # The caller's existing total deadline still bounds the entire loop.
    if at_bundled_gateway(config.base_url):
        body["timeout"] = timeout_seconds
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds, connect=min(10, timeout_seconds))) as client:
            response = await client.post(url, headers={"Authorization": f"Bearer {config.api_key}"}, json=body)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("invalid_model_response")
    except Exception as exc:
        llm_health.record_failure(type(exc).__name__)
        raise
    llm_health.record_success()
    return payload
