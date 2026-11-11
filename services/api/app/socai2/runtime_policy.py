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
    if (not isinstance(data, dict) or set(data) != {"version", "render", "system_prompt", "output_validation"}
            or data["version"] != "socai2.alert-boundary.v1" or not isinstance(data["render"], dict)
            or not isinstance(data["system_prompt"], str) or not data["system_prompt"].strip()
            or data["output_validation"] != {"prose_alias_format": "namespaced_v1"}):
        raise ValueError("alert_profile_contract_invalid")
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
    if (not isinstance(output, dict) or set(output) != {"max_followups", "instruction"}
            or type(output["max_followups"]) is not int or not 0 <= output["max_followups"] <= 12
            or not isinstance(output["instruction"], str) or "{max_followups}" not in output["instruction"]):
        # 12 is the existing storage contract's capacity, not a runtime default.
        raise ValueError("case_c3_output_policy_invalid")
    program = data.get("program_output")
    if (not isinstance(program, dict) or set(program) != {"version", "instruction"}
            or program["version"] != "socai2.case-program-output.v1"
            or not isinstance(program["instruction"], str) or not program["instruction"].strip()):
        raise ValueError("case_program_output_policy_invalid")
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
    incident_io: object = None
    alert_io: object = None
    case_io: object = None

    @property
    def identity(self):
        return self.version + ":" + self.sha256[:12]


def load_policy(path):
    raw = Path(path).read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))
    if set(data) - {"incident_io", "alert_io", "case_io"} != {"version", "single_model_timeout_seconds", "final_reserve_seconds", "case", "alert_basic", "incident_diagnosis", "model", "tools", "labels"}:
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
    if "incident_io" in data:
        incident_io = load_incident_profile(data["incident_io"])
    alert_io = load_alert_profile(data["alert_io"]) if "alert_io" in data else None
    case_io = load_case_profile(data["case_io"]) if "case_io" in data else None
    return InvestigationPolicy(version=data["version"], sha256=hashlib.sha256(raw).hexdigest(), incident_io=incident_io, alert_io=alert_io, case_io=case_io,
        single_model_timeout_seconds=data["single_model_timeout_seconds"],
        final_reserve_seconds=data["final_reserve_seconds"], model=ModelPolicy.parse(data["model"]),
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
    max_artifact_bytes: int
    final_reserved_input_tokens: int
    final_reserved_calls: int
    output_tokens: object
    tokenizer: object

    @classmethod
    def parse(cls, values):
        if not isinstance(values, dict) or set(values) != set(cls.__dataclass_fields__):
            raise ValueError("model_policy_configuration_incomplete")
        for key in ("alias", "protocol", "schema_profile"):
            if not isinstance(values[key], str) or not values[key].strip():
                raise ValueError("model_policy_identity_invalid")
        if values["protocol"] != "chat_completions":
            raise ValueError("model_policy_token_meter_protocol_not_supported")
        for key in ("context_tokens", "max_prepared_bytes", "max_artifact_bytes", "final_reserved_input_tokens", "final_reserved_calls"):
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
    """Preparation/storage ceiling; final token measurement decides model fit."""
    return active_policy().model.max_prepared_bytes


def field_limit():
    # A single field shares the preparation allowance; no separate 2 KiB cut.
    return draft_limit()


def retention_limit():
    return active_policy().model.max_artifact_bytes
