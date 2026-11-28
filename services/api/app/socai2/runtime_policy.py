"""Explicit, immutable process policy; no environment-specific values in code."""

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from urllib.parse import urlsplit

import tomllib


@dataclass(frozen=True)
class IncidentProfile:
    version: str
    sha256: str
    raw: bytes

    @property
    def config(self):
        return json.loads(self.raw)


def load_incident_profile(selection):
    # Keep the deployment policy validator dependency-free and loadable as a
    # standalone module, including inside the candidate image self-test.
    if not isinstance(selection, dict) or set(selection) != {"profile"}:
        raise ValueError("incident_profile_selection_invalid")
    name = selection["profile"]
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(".json"):
        raise ValueError("incident_profile_name_invalid")
    raw = Path(__file__).with_name(name).read_bytes()
    data = json.loads(raw)
    if (not isinstance(data, dict) or set(data) - {"output_validation"} != {"version", "render", "system_prompt"}
            or data["version"] != "socai2.incident-boundary.v1" or not isinstance(data["render"], dict)
            or not isinstance(data["system_prompt"], str) or not data["system_prompt"].strip()):
        raise ValueError("incident_profile_contract_invalid")
    if "output_validation" in data and data["output_validation"] != {"prose_alias_format": "namespaced_v1"}:
        raise ValueError("incident_profile_output_validation_invalid")
    return IncidentProfile(data["version"], hashlib.sha256(raw).hexdigest(), raw)


def load_alert_profile(selection):
    if not isinstance(selection, dict) or set(selection) != {"profile"}:
        raise ValueError("alert_profile_selection_invalid")
    name = selection["profile"]
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(".json"):
        raise ValueError("alert_profile_name_invalid")
    raw = Path(__file__).with_name(name).read_bytes()
    data = json.loads(raw)
    if (not isinstance(data, dict)
            or set(data) - {"no_escalation_min_confidence"} != {"version", "render", "system_prompt", "output_validation"}
            or data["version"] != "socai2.alert-boundary.v1" or not isinstance(data["render"], dict)
            or not isinstance(data["system_prompt"], str) or not data["system_prompt"].strip()
            or data["output_validation"] != {"prose_alias_format": "namespaced_v1"}):
        raise ValueError("alert_profile_contract_invalid")
    if "no_escalation_min_confidence" in data:
        threshold = data["no_escalation_min_confidence"]
        if type(threshold) not in {int, float} or not 0 < threshold <= 1:
            raise ValueError("alert_profile_no_escalation_threshold_invalid")
    return IncidentProfile(data["version"], hashlib.sha256(raw).hexdigest(), raw)


@dataclass(frozen=True)
class CaseProfile(IncidentProfile):
    business_raw: bytes

    @property
    def business(self):
        return json.loads(self.business_raw)

    @property
    def identity(self):
        return {"version": self.version, "sha256": self.sha256,
                "business_sha256": hashlib.sha256(self.business_raw).hexdigest()}


C3_COMPLETION_VERSION = "socai2.c3-completion.v1"
C3_SECTIONS = ("summary", "members", "findings", "questions", "domains", "conflicts", "followups")


def validate_c3_completion(policy, *, frozen=False):
    keys = {"version", "max_attempts", "instruction", "dependencies"} | ({"system"} if frozen else set())
    if (not isinstance(policy, dict) or set(policy) != keys or policy.get("version") != C3_COMPLETION_VERSION
            or type(policy.get("max_attempts")) is not int or policy["max_attempts"] not in {0, 1}
            or not isinstance(policy.get("instruction"), str) or "{missing}" not in policy["instruction"]
            or not isinstance(policy.get("dependencies"), dict) or set(policy["dependencies"]) != set(C3_SECTIONS)
            or any(not isinstance(v, list) or any(k not in C3_SECTIONS for k in v) or len(v) != len(set(v))
                   for v in policy["dependencies"].values())
            or (frozen and (not isinstance(policy.get("system"), str) or not policy["system"].strip()))):
        raise ValueError("case_c3_completion_policy_invalid")



def validate_material_mirrors(rules):
    # Remain standalone: deployment validation imports this module directly.
    def path(value):
        return (isinstance(value, str) and value.startswith("$.raw_json.raw_event.")
                and all(part.isidentifier() for part in value[2:].split(".")))

    if (not isinstance(rules, list)
            or any(not isinstance(rule, dict) or set(rule) != {"source_path", "object_path"}
                   or not all(path(rule[key]) for key in ("source_path", "object_path"))
                   or rule["source_path"] == rule["object_path"] for rule in rules)
            or len({rule["source_path"] for rule in rules}) != len(rules)):
        raise ValueError("case_material_mirrors_invalid")


def validate_material_backend_paths(policy):
    paths = policy.get("material_backend_paths")
    referenced = policy.get("material_backend_reference_paths", [])
    if (any(not isinstance(group, list) or any(
            not isinstance(path, str) or not path.startswith("$.raw_json.")
            or not all(part.isidentifier() for part in path[2:].split(".")) for path in group)
            or len(group) != len(set(group)) for group in (paths, referenced))
            or not set(referenced) <= set(paths)):
        raise ValueError("case_material_backend_paths_invalid")


def validate_material_unmapped_paths(policy):
    # This Case-only boundary deliberately cannot become a recursive key filter.
    allowed = {
        "material_unmapped_paths": {"$.ocsf_json.unmapped", "$.raw_json.raw_event.ocsf_event.unmapped"},
        "material_unmapped_serialized_paths": {"$.raw_text", "$.raw_json.raw_event.source_ocsf_json",
            "$.ocsf_json.raw_data", "$.raw_json.raw_event.ocsf_event.raw_data"},
    }
    for key, paths in allowed.items():
        value = policy.get(key, [])
        if (not isinstance(value, list) or any(not isinstance(path, str) or path not in paths for path in value)
                or len(value) != len(set(value))):
            raise ValueError("case_material_unmapped_paths_invalid")
    if policy.get("material_unmapped_serialized_paths") and not policy.get("material_unmapped_paths"):
        raise ValueError("case_material_unmapped_paths_invalid")


def load_case_profile(selection):
    if not isinstance(selection, dict) or set(selection) != {"profile"}:
        raise ValueError("case_profile_selection_invalid")
    name = selection["profile"]
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(".json"):
        raise ValueError("case_profile_name_invalid")
    raw = Path(__file__).with_name(name).read_bytes()
    data = json.loads(raw)
    if (not isinstance(data, dict) or data.get("version") != "socai2.case-boundary.v1"
            or not isinstance(data.get("rules"), dict) or not isinstance(data.get("hierarchy"), dict)):
        raise ValueError("case_profile_contract_invalid")
    projections, meanings, questions = data.get("context_projection"), data.get("field_meanings"), data.get("question_instructions")
    if (not isinstance(projections, dict) or any(not isinstance(path, str) or not path.startswith("$.")
            or not isinstance(rule, dict) or set(rule) != {"omit", "empty"}
            or any(not isinstance(rule[k], list) or any(not isinstance(f, str) for f in rule[k]) for k in ("omit", "empty"))
            for path, rule in projections.items())
            or not isinstance(meanings, list) or any(not isinstance(rule, dict) or set(rule) != {"paths", "meaning"}
                or not isinstance(rule["paths"], list) or not rule["paths"] or any(not isinstance(p, str) for p in rule["paths"])
                or not isinstance(rule["meaning"], str) or not rule["meaning"].strip() for rule in meanings)
            or not isinstance(questions, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not v.strip()
                                                     for k, v in questions.items())):
        raise ValueError("case_context_meaning_policy_invalid")
    output = data.get("c3_output")
    if (not isinstance(output, dict) or set(output) != {"version", "max_findings", "max_followups", "instruction"}
            or output["version"] != "socai2.c3-output.v1"
            or type(output["max_findings"]) is not int or not 0 <= output["max_findings"] <= 24
            or type(output["max_followups"]) is not int or not 0 <= output["max_followups"] <= 12
            or not isinstance(output["instruction"], str)
            or any(field not in output["instruction"] for field in ("{max_findings}", "{max_followups}"))):
        # 24/12 are existing storage capacities, not runtime defaults.
        raise ValueError("case_c3_output_policy_invalid")
    validate_c3_completion(data.get("c3_completion"))
    routing = data.get("followup_routing")
    if (not isinstance(routing, dict) or set(routing) != {"version", "C3", "Deep"}
            or routing["version"] != "socai2.followup-routing.v1"
            or any(not isinstance(routing[k], str) or not routing[k].strip() for k in ("C3", "Deep"))):
        raise ValueError("case_followup_routing_policy_invalid")
    program = data.get("program_output")
    if (not isinstance(program, dict) or not {"version", "instruction"} <= set(program)
            or set(program) - {"version", "instruction", "c3_coverage"}
            or ("c3_coverage" in program and type(program["c3_coverage"]) is not bool)
            or program["version"] not in {"socai2.case-program-output.v1", "socai2.case-program-output.v2"}
            or not isinstance(program["instruction"], str) or not program["instruction"].strip()):
        raise ValueError("case_program_output_policy_invalid")
    comparison = data.get("fixed_comparison")
    if comparison is not None and (not isinstance(comparison, dict)
            or set(comparison) != {"version", "summary", "instruction"}
            or comparison["version"] != "socai2.case-fixed-comparison.v1"
            or any(not isinstance(comparison[k], str) or not comparison[k].strip()
                   for k in ("summary", "instruction")) or len(comparison["summary"]) > 1200):
        raise ValueError("case_fixed_comparison_policy_invalid")
    comparison_input = data.get("comparison_input_selection")
    if comparison_input is not None and (not isinstance(comparison_input, dict)
            or set(comparison_input) != {"version", "omit", "question_states", "exclude_questions", "instruction"}
            or comparison_input["version"] != "fixed-comparison-business-v1"
            or not isinstance(comparison_input["omit"], dict)
            or set(comparison_input["omit"]) != {"findings", "questions", "case_impact"}
            or any(not isinstance(v, list) or any(not isinstance(k, str) for k in v)
                   for v in [*comparison_input["omit"].values(), comparison_input["question_states"], comparison_input["exclude_questions"]])
            or not isinstance(comparison_input["instruction"], str) or not comparison_input["instruction"].strip()):
        raise ValueError("case_comparison_input_policy_invalid")
    enrichment = data.get("enrichment")
    if (not isinstance(enrichment, dict) or set(enrichment) != {
            "version", "reserved_tool_calls", "paired_source_penalty", "priorities"}
            or enrichment["version"] != "socai2.case-background-coverage.v1"
            or any(type(enrichment[k]) is not int or enrichment[k] < 0
                   for k in ("reserved_tool_calls", "paired_source_penalty"))
            or not isinstance(enrichment["priorities"], dict)
            or set(enrichment["priorities"]) != {"assets", "history", "threat_intel", "ueba", "knowledge", "graph"}
            or any(type(v) is not int or v < 0 for v in enrichment["priorities"].values())
            or not isinstance(data.get("citation_instruction"), str) or not data["citation_instruction"].strip()):
        raise ValueError("case_profile_enrichment_or_citation_invalid")
    followup = data.get("followup")
    c3_selection, c6_selection = data.get("c3_input_selection", {}), data.get("followup_input_selection", {})
    validate_material_backend_paths(c3_selection)
    validate_material_mirrors(c3_selection.get("material_mirrors", []))
    validate_material_unmapped_paths(c3_selection)
    if (any(key in c3_selection and type(c3_selection[key]) is not bool
            for key in ("omit_unusable_prior_results", "prefer_incident_conclusion"))
            or "defer_prior_context" in c6_selection and type(c6_selection["defer_prior_context"]) is not bool
            or not isinstance(c6_selection.get("final_prior_omit", []), list)
            or any(v not in {"members", "domains"} for v in c6_selection.get("final_prior_omit", []))
            or not isinstance(c6_selection.get("graph_directory_relations", []), list)
            or any(v != "source_reports_object" for v in c6_selection.get("graph_directory_relations", []))):
        raise ValueError("case_task_input_selection_invalid")
    knowledge = data.get("knowledge_selection", {}).get("stage_max_characters")
    if (not isinstance(knowledge, dict) or set(knowledge) != {"C3", "Deep", "C6"}
            or any(type(v) is not int or v < 0 for v in knowledge.values())):
        raise ValueError("case_knowledge_selection_invalid")
    purposes = data["knowledge_selection"].get("stage_purposes")
    if (not isinstance(purposes, dict) or set(purposes) != {"C3", "Deep", "C6"}
            or any(not isinstance(v, list) or not v or not set(v) <= {
                "technical_explanation", "investigation_guidance", "historical_case_reference"} for v in purposes.values())):
        raise ValueError("case_knowledge_stage_purposes_invalid")
    for stage, key in (("Deep", "deep_question_purposes"), ("C6", "final_question_purposes")):
        question_purposes = data["knowledge_selection"].get(key, {})
        if (not isinstance(question_purposes, dict)
                or any(not isinstance(k, str) or not k.strip() or not isinstance(v, list)
                       or any(not isinstance(p, str) or p not in purposes[stage] for p in v)
                       for k, v in question_purposes.items())):
            raise ValueError("case_knowledge_question_purposes_invalid")
    if (not isinstance(followup, dict) or followup.get("version") != "socai2.case-followup.v1"
            or any(not isinstance(followup.get(k), str) or not followup[k].strip() for k in ("Deep", "C6", "common"))
            or any(not isinstance(followup.get(k), list) or any(not isinstance(v, str) for v in followup[k])
                   for k in ("query_omit", "execution_omit", "comparison_omit", "comparison_source_omit", "prior_followup_omit"))
            or not isinstance(followup.get("parent_dependencies"), list)
            or not isinstance(followup.get("labels"), dict)
            or not {"base", "case_record", "query_receipt", "background_status", "C3", "Deep", "query", "plan", "comparison", "graph", "dependency"} <= set(followup["labels"])):
        raise ValueError("case_followup_profile_contract_invalid")
    business = load_incident_profile({"profile": data["business_profile"]})
    return CaseProfile(data["version"], hashlib.sha256(raw).hexdigest(), raw, business.raw)


@dataclass(frozen=True)
class StagePolicy:
    max_model_calls: int
    max_tool_calls: int
    max_total_tokens: int
    max_rows_per_query: int
    deadline_seconds: int

    def limits(self, now, version):
        from .baseline_contracts import Limits
        return Limits(max_model_calls=self.max_model_calls, max_tool_calls=self.max_tool_calls,
            max_tokens=self.max_total_tokens, max_rows_per_query=self.max_rows_per_query,
            deadline_at=now + timedelta(seconds=self.deadline_seconds), policy_version=version)

    def allows(self, limits, now):
        return all(value is not None and value <= maximum for value, maximum in (
            (limits.max_model_calls, self.max_model_calls), (limits.max_tool_calls, self.max_tool_calls),
            (limits.max_tokens, self.max_total_tokens), (limits.max_rows_per_query, self.max_rows_per_query))) and (
                limits.deadline_at is not None and (limits.deadline_at - now).total_seconds() <= self.deadline_seconds)


@dataclass(frozen=True)
class InvestigationPolicy:
    version: str
    sha256: str
    single_model_timeout_seconds: int
    final_reserve_seconds: int
    case: StagePolicy
    alert_basic: StagePolicy
    incident_diagnosis: StagePolicy
    model: object
    tools: object
    labels: object
    views: object
    raw: bytes
    incident_io: object = None
    alert_io: object = None
    case_io: object = None
    query_transport: object = None

    @property
    def identity(self):
        return self.version + ":" + self.sha256[:12]

    def require_execution_profiles(self, *names):
        """Historical policies can be read, but cannot select old execution contracts."""
        for name in names or ("alert_io", "incident_io", "case_io"):
            profile = getattr(self, name, None)
            if profile is None:
                raise ValueError("execution_profile_required:" + name)
            if name in {"alert_io", "incident_io"}:
                if profile.config.get("output_validation") != {"prose_alias_format": "namespaced_v1"}:
                    raise ValueError("execution_profile_not_current:" + name)
            elif name == "case_io":
                program = profile.config["program_output"]
                if program["version"] != "socai2.case-program-output.v2" or program.get("c3_coverage") is not True:
                    raise ValueError("execution_profile_not_current:" + name)
            else:
                raise ValueError("execution_profile_unknown:" + name)
        return self

    def snapshot(self):
        """Validated configuration only, never process environment or secrets."""
        profiles = {}
        for name in ("alert_io", "incident_io", "case_io"):
            profile = getattr(self, name)
            if profile is not None:
                profiles[name] = {"sha256": profile.sha256, "json_text": profile.raw.decode("utf-8")}
                if isinstance(profile, CaseProfile):
                    profiles[name]["business"] = {
                        "sha256": hashlib.sha256(profile.business_raw).hexdigest(),
                        "json_text": profile.business_raw.decode("utf-8")}
        return {"schema_version": "socai2.runtime-policy.v1", "policy_id": self.identity,
                "sha256": self.sha256, "toml_text": self.raw.decode("utf-8"), "profiles": profiles}


def load_policy(path):
    raw = Path(path).read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))
    if set(data) - {"incident_io", "alert_io", "case_io", "query_transport"} != {"version", "single_model_timeout_seconds", "final_reserve_seconds", "case", "alert_basic", "incident_diagnosis", "model", "tools", "labels", "views"}:
        raise ValueError("investigation_policy_configuration_incomplete")
    if not isinstance(data["version"], str) or not data["version"].strip() or len(data["version"]) > 100:
        raise ValueError("investigation_policy_version_invalid")
    for key in ("single_model_timeout_seconds", "final_reserve_seconds"):
        if type(data[key]) is not int or data[key] <= 0:
            raise ValueError("investigation_policy_time_invalid")
    stages = {}
    for name in ("case", "alert_basic", "incident_diagnosis"):
        values = data[name]
        if not isinstance(values, dict) or set(values) != set(StagePolicy.__dataclass_fields__):
            raise ValueError("investigation_policy_stage_incomplete")
        if any(type(v) is not int or v < 0 for v in values.values()) or values["deadline_seconds"] <= 0:
            raise ValueError("investigation_policy_allowance_invalid")
        stages[name] = StagePolicy(**values)
    if not data["single_model_timeout_seconds"] <= data["final_reserve_seconds"] < stages["case"].deadline_seconds:
        raise ValueError("investigation_policy_final_reservation_invalid")
    tools = data["tools"]
    if not isinstance(tools, dict) or not tools:
        raise ValueError("investigation_policy_tool_catalog_missing")
    for spec in tools.values():
        if (not isinstance(spec, dict) or set(spec) != {"purpose", "inputs", "can_answer", "cannot_answer"}
                or any(not isinstance(v, str) or not v.strip() for v in spec.values())):
            raise ValueError("investigation_policy_tool_description_invalid")
    labels = data["labels"]
    if (not isinstance(labels, dict) or set(labels) != {"version", "entries"}
            or not isinstance(labels["version"], str) or not labels["version"].strip()
            or not isinstance(labels["entries"], dict)):
        raise ValueError("investigation_policy_label_dictionary_invalid")
    for identity, spec in labels["entries"].items():
        if (not isinstance(identity, str) or not identity or not isinstance(spec, dict)
                or set(spec) != {"name", "description", "source_url", "verified_on"}
                or any(not isinstance(v, str) or not v.strip() for v in spec.values())
                or urlsplit(spec["source_url"]).scheme != "https"):
            raise ValueError("investigation_policy_label_entry_invalid")
    incident_io = None
    views = data["views"]
    if (not isinstance(views, dict) or set(views) != {"max_graph_bytes"}
            or type(views["max_graph_bytes"]) is not int or views["max_graph_bytes"] <= 16384):
        raise ValueError("investigation_policy_view_capacity_invalid")
    if "incident_io" in data:
        incident_io = load_incident_profile(data["incident_io"])
    alert_io = load_alert_profile(data["alert_io"]) if "alert_io" in data else None
    case_io = load_case_profile(data["case_io"]) if "case_io" in data else None
    transport = data.get("query_transport")
    if transport is not None and (not isinstance(transport, dict) or set(transport) != {
            "query_timeout_seconds", "connect_timeout_seconds", "send_receive_timeout_seconds", "close_timeout_seconds"}
            or any(type(v) not in {int, float} or not 0 < v < float("inf") for v in transport.values())
            or transport["query_timeout_seconds"] < 1):
        raise ValueError("query_transport_policy_invalid")
    return InvestigationPolicy(version=data["version"], sha256=hashlib.sha256(raw).hexdigest(), incident_io=incident_io, alert_io=alert_io, case_io=case_io,
        query_transport=MappingProxyType(transport) if transport is not None else None,
        single_model_timeout_seconds=data["single_model_timeout_seconds"],
        final_reserve_seconds=data["final_reserve_seconds"], model=ModelPolicy.parse(data["model"]),
        views=MappingProxyType(views), raw=raw,
        tools=MappingProxyType({k: MappingProxyType(v) for k, v in tools.items()}),
        labels=MappingProxyType({"version": labels["version"], "entries": MappingProxyType({
            k: MappingProxyType(v) for k, v in labels["entries"].items()})}), **stages)


@dataclass(frozen=True)
class ModelPolicy:
    alias: str
    protocol: str
    schema_profile: str
    context_tokens: int
    max_prepared_bytes: int
    final_reserved_input_tokens: int
    final_reserved_calls: int
    output_tokens: object
    tokenizer: object
    incident_max_structure_whitespace: int | None = None

    @classmethod
    def parse(cls, values):
        whitespace_key = "incident_max_structure_whitespace"
        required = set(cls.__dataclass_fields__) - {whitespace_key}
        if not isinstance(values, dict) or set(values) - {whitespace_key} != required:
            raise ValueError("model_policy_configuration_incomplete")
        for key in ("alias", "protocol", "schema_profile"):
            if not isinstance(values[key], str) or not values[key].strip():
                raise ValueError("model_policy_identity_invalid")
        if values["protocol"] != "chat_completions":
            raise ValueError("model_policy_token_meter_protocol_not_supported")
        if whitespace_key in values and (type(values[whitespace_key]) is not int
                or values[whitespace_key] < 0 or values["schema_profile"] != "vllm_grammar_v1"):
            raise ValueError("model_policy_incident_whitespace_invalid")
        for key in ("context_tokens", "max_prepared_bytes", "final_reserved_input_tokens", "final_reserved_calls"):
            if type(values[key]) is not int or values[key] <= 0:
                raise ValueError("model_policy_capacity_invalid")
        outputs, tokenizer = values["output_tokens"], values["tokenizer"]
        if not isinstance(outputs, dict) or set(outputs) != {"A", "I", "C3", "Deep", "C6"} or any(type(v) is not int or not 0 < v < values["context_tokens"] for v in outputs.values()):
            raise ValueError("model_policy_outputs_invalid")
        if not isinstance(tokenizer, dict) or set(tokenizer) != {"endpoint", "served_model", "timeout_seconds", "safety_tokens", "authentication"}:
            raise ValueError("model_policy_tokenizer_incomplete")
        url = urlsplit(tokenizer["endpoint"])
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("model_policy_tokenizer_endpoint_invalid")
        if tokenizer["authentication"] != "none" or not isinstance(tokenizer["served_model"], str) or not tokenizer["served_model"].strip():
            raise ValueError("model_policy_tokenizer_identity_invalid")
        if any(type(tokenizer[k]) is not int or tokenizer[k] <= 0 for k in ("timeout_seconds", "safety_tokens")):
            raise ValueError("model_policy_tokenizer_allowance_invalid")
        if values["final_reserved_input_tokens"] + outputs["C6"] + tokenizer["safety_tokens"] > values["context_tokens"]:
            raise ValueError("model_policy_final_reservation_invalid")
        return cls(**{**values, "output_tokens": MappingProxyType(outputs), "tokenizer": MappingProxyType(tokenizer)})


@lru_cache(maxsize=1)
def active_policy():
    # Policy cannot change midway through a process/Run. Select a file and
    # restart the process to activate another reviewed configuration.
    from .baseline_store import StoreError
    path = os.environ.get("SOCAI2_INVESTIGATION_POLICY")
    if not path or not Path(path).is_absolute():
        raise StoreError("investigation_policy_file_required", 503)
    try:
        return load_policy(path)
    except (OSError, ValueError, TypeError):
        raise StoreError("investigation_policy_file_invalid", 503) from None


def draft_limit():
    """Model-view preparation ceiling; never an original storage/read limit."""
    return active_policy().model.max_prepared_bytes


def execution_policy(*profiles):
    from .baseline_store import StoreError
    policy = active_policy()
    try:
        return policy.require_execution_profiles(*profiles)
    except ValueError:
        raise StoreError("investigation_execution_contract_required", 503) from None


def field_limit():
    # A single field shares the preparation allowance; no separate 2 KiB cut.
    return draft_limit()


def graph_limit():
    """Derived C5 view allowance; retained originals are stored independently."""
    return active_policy().views["max_graph_bytes"]
