"""Candidate Case requests from a pinned export; tokenizer only, private reports.

The legacy replay_v12_capacity.rebuild assumes the old JSON model view and a
legacy fake store. Only its immutable-export approach applies here. This entry
uses the current Case builders directly and never resumes or persists a Run.
"""
import argparse
import asyncio
import contextlib
import copy
import hashlib
import ipaddress
import json
import logging
import os
import sys
import traceback
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from urllib.parse import urlsplit


class Unavailable(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Unavailable(reason)


def save(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as output:
        json.dump(value, output, ensure_ascii=False, indent=2, allow_nan=False)


def pinned_file(spec):
    content = Path(spec["path"]).read_bytes()
    require(hashlib.sha256(content).hexdigest() == spec["sha256"], "pinned_file_changed")
    return content


def tokenizer_endpoint(value):
    try:
        endpoint = urlsplit(value)
        loopback = ipaddress.ip_address(endpoint.hostname).is_loopback
    except ValueError:
        raise Unavailable("existing_loopback_tokenizer_required") from None
    require(endpoint.scheme in {"http", "https"} and endpoint.path.endswith("/tokenize")
            and not any((endpoint.username, endpoint.password, endpoint.query, endpoint.fragment))
            and loopback, "existing_loopback_tokenizer_required")
    return endpoint


def load_config(path):
    from jsonschema import Draft202012Validator, FormatChecker
    config = json.loads(path.read_bytes())
    schema = json.loads(Path(__file__).with_name("case-input-capacity-config.schema.json").read_bytes())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(config)
    for value in (config["snapshot"]["path"], config["policy"]["path"], config["output_dir"]):
        require(Path(value).is_absolute(), "absolute_path_required")
    require(Path(config["output_dir"]).resolve() == path.parent.resolve(), "output_must_be_config_directory")
    tokenizer_endpoint(config["tokenizer"]["endpoint"])
    return config


def configure(config):
    from app.socai2.runtime_policy import active_policy
    pinned_file(config["policy"])
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = config["policy"]["path"]
    active_policy.cache_clear()
    policy = active_policy()
    policy.require_execution_profiles("case_io")
    require(policy.case_io.identity == config["candidate_case_profile"], "candidate_profile_changed")
    original, local = urlsplit(policy.model.tokenizer["endpoint"]), urlsplit(config["tokenizer"]["endpoint"])
    require(original.scheme == local.scheme and original.path == local.path, "tokenizer_mapping_must_preserve_route")
    require(policy.model.protocol == "chat_completions", "local_chat_tokenizer_profile_required")
    # Only the host/port mapping changes; all model identities and budgets are
    # still the values from the explicitly pinned original policy file.
    meter_policy = replace(policy.model, tokenizer=MappingProxyType({
        **policy.model.tokenizer, "endpoint": config["tokenizer"]["endpoint"]}))
    return policy, meter_policy


class Frozen:
    def __init__(self, config):
        self.data = json.loads(pinned_file(config["snapshot"]))
        self.selection = config["artifacts"]
        runs = [row for row in self.data["runs"] if row["id"] == config["run_id"]]
        require(len(runs) == 1, "selected_run_unavailable_or_ambiguous")
        self.run = runs[0]
        rows = [row for row in self.data["artifacts"] if row["run_id"] == self.run["id"]]
        self.rows = {row["id"]: row for row in rows}
        require(len(self.rows) == len(rows), "duplicate_frozen_artifact")
        require(all(row["tenant_id"] == self.run["tenant_id"] for row in rows), "frozen_artifact_invalid")
        self.steps = {row["id"]: row for row in self.data["run_steps"] if row["run_id"] == self.run["id"]}

    def artifact(self, identity):
        from app.socai2.baseline_store import digest
        require(identity is not None and identity in self.rows, "required_frozen_artifact_unavailable")
        row = self.rows[identity]
        # Only selected JSON sources require JSON content integrity. The full
        # export also legitimately contains text/blob/unavailable artifacts.
        require(isinstance(row["content_json"], dict) and digest(row["content_json"]) == row["sha256"],
                "frozen_artifact_invalid")
        return row

    def selected(self, key, stages=()):
        row = self.artifact(self.selection[key])
        if stages:
            step = self.steps.get(row.get("step_id"))
            require(step is not None and step["stage_code"] in stages, "frozen_stage_receipt_mismatch")
        return row


def base_input(frozen, policy, output):
    from app.socai2 import baseline_enrichment, case_model_boundary
    from app.socai2.baseline_context import PROJECTION, SCHEMA, Context
    source = frozen.selected("context")
    manifest = frozen.artifact(frozen.run["input_artifact_id"])
    require(manifest["kind"] == "input_snapshot" and manifest["content_json"].get("projection_version") == PROJECTION
            and source["kind"] == "source_snapshot" and source["schema_version"] == SCHEMA
            and source.get("case_id") == frozen.run["case_id"]
            and any(ref.get("type") == "artifact" and ref.get("id") == source["id"]
                    for ref in manifest["content_json"]["source_materials"]), "selected_context_not_frozen_c1_input")
    original = Context.model_validate(source["content_json"])
    require(str(original.case_id) == frozen.run["case_id"], "frozen_case_mismatch")
    require(frozen.run["limits"]["policy_version"] == policy.identity, "frozen_run_policy_mismatch")
    context = original.model_copy(deep=True, update={"case_input_profile": copy.deepcopy(policy.case_io.identity)})
    save(output / "candidate-context-identity.json", {"mode": "candidate_rebuild_not_run_continuation",
        "original_context_artifact_id": source["id"], "original_context_sha256": source["sha256"],
        "original_profile": original.case_input_profile, "candidate_profile": context.case_input_profile})
    summary = frozen.selected("enrichment_summary", ("C2",))["content_json"]
    require(summary.get("schema_version") == baseline_enrichment.SCHEMA and isinstance(summary.get("sources"), list),
            "frozen_background_summary_unavailable")
    received, states = [], []
    for item in summary["sources"]:
        artifact = frozen.artifact(item["artifact_id"])
        payload = artifact["content_json"]
        received.append((artifact["id"], payload, baseline_enrichment.citation_roles(payload)))
        states.append({**{key: item[key] for key in ("source", "outcome", "truncated", "reason", "limitations")},
                       "captured_at": payload["captured_at"]})
    materials = {}
    for aid, member in context.alerts.items():
        if member.material is not None:
            rows = [row for row in frozen.data["alert_materials"] if row["id"] == member.material["id"]]
            require(len(rows) == 1 and rows[0]["alert_id"] == aid, "frozen_member_material_unavailable")
            materials[aid] = rows[0]
    prepared = case_model_boundary.build(context, source["id"], received, states, materials,
        execution_time=frozen.run["started_at"], run_id=frozen.run["id"])
    save(output / "base-prepared.json", prepared)
    require(prepared["ready"], "candidate_base_input_unavailable")
    return context, prepared


def request_body(policy, stage, messages, fmt):
    from app.socai2.baseline_execution_schema import compact_execution_wire
    from app.socai2.model_protocol import prepare_request
    gateway = SimpleNamespace(provider=policy.model.protocol, schema_profile=policy.model.schema_profile)
    body = prepare_request(gateway, {"model": policy.model.alias, "messages": messages,
        "max_tokens": policy.model.output_tokens[stage], "temperature": 0, "response_format": fmt})
    return compact_execution_wire(body) if stage == "C3" else body


def c3_request(frozen, context, base, policy, output):
    from app.socai2 import case_model_boundary, case_output_adapter
    from app.socai2.baseline_evidence_tools import binding_subject
    row = frozen.selected("c3_bindings", ("C3",))
    payload = row["content_json"]
    if row["kind"] == "model_request" and payload.get("direction") == "request":
        payload = payload["payload"]
    else:
        require(payload.get("type") == "capacity_preflight" and payload.get("stage") == "C3"
                and payload.get("dispatch_state") == "not_sent", "frozen_binding_receipt_unavailable")
    require(isinstance(payload.get("binding_map"), dict), "frozen_offered_bindings_unavailable")
    require(payload["body"]["model"] == policy.model.alias
            and payload["body"]["max_tokens"] == policy.model.output_tokens["C3"], "frozen_binding_model_mismatch")
    bindings = copy.deepcopy(payload["binding_map"])
    options = [{"binding_id": alias, "tool_name": binding["tool_name"], **binding_subject(binding),
                "alert_ids": binding["alert_ids"], "object_keys": sorted({o["object_key"] for o in binding["objects"]})}
               for alias, binding in bindings.items()]
    # These options were actually offered in the frozen request. No current
    # clock, fabricated availability, tool discovery or live query is involved.
    prepared = copy.deepcopy(base)
    messages, _ = case_model_boundary.messages(prepared, context, options)
    bindings = {alias: binding for alias, binding in bindings.items()
                if alias in {option["binding_id"] for option in options}}
    fmt = case_output_adapter.output_format(prepared, context, bindings)
    save(output / "prepared.json", prepared)
    return request_body(policy, "C3", messages, fmt)


def c6_request(frozen, context, base, policy, output):
    from app.socai2 import case_followup_input
    from app.socai2.baseline_context import reference
    from app.socai2.baseline_followup_projection import delivery_followups
    from app.socai2.case_followup_loader import graph_candidates
    from app.socai2.case_followup_output import final_format
    report_row = frozen.selected("c6_report", ("C6",))
    report = report_row["content_json"]
    require(report.get("type") == "delivery_report", "frozen_delivery_report_unavailable")
    cutoff = frozen.steps[report_row["step_id"]]["seq"]
    started_at = datetime.fromisoformat(frozen.steps[report_row["step_id"]]["started_at"])
    require(started_at.tzinfo is not None, "c6_stage_time_not_aware")
    artifacts = {}
    for identity, row in frozen.rows.items():
        if row["content_json"] is None or row["kind"] in {"model_request", "model_response"}:
            continue
        step = frozen.steps.get(row.get("step_id"))
        require(step is not None or row.get("step_id") is None, "frozen_artifact_step_unavailable")
        captured_at = datetime.fromisoformat(row["captured_at"])
        require(captured_at.tzinfo is not None, "frozen_artifact_time_not_aware")
        # C1 Context/policy/page-model artifacts normally have no step_id.
        # Their already verified Run/tenant and recorded time prove existence;
        # missing time or an unknown non-null step never means 'latest'.
        if (step is None or step["seq"] < cutoff) and captured_at <= started_at:
            artifacts[identity] = frozen.artifact(identity)
    comparison = report["comparison"]
    prior = frozen.selected("c3_result", ("C3", "C3.reanalysis"))
    require(prior["id"] in artifacts, "selected_prior_not_before_c6")
    require("analysis" in prior["content_json"], "frozen_c3_result_unavailable")
    prior_step = frozen.steps[prior["step_id"]]
    completed = [step for step in frozen.steps.values() if step["kind"] == "stage"
                 and step["stage_code"] in {"C3", "C3.reanalysis"} and step["state"] == "completed"
                 and step["seq"] < cutoff]
    if completed:
        require(prior_step["id"] == max(completed, key=lambda step: step["seq"])["id"],
                "selected_prior_is_not_recorded_c6_predecessor")
        previous, prior_id = prior["content_json"], prior["id"]
    else:
        previous, prior_id = None, None
    dispatch_row = frozen.selected("c4_dispatch", ("C4.routing",))
    require(dispatch_row["id"] in artifacts, "selected_dispatch_not_before_c6")
    dispatch = dispatch_row["content_json"]
    require(dispatch.get("type") == "followup_dispatch", "frozen_dispatch_unavailable")
    require(dispatch["initial_analysis_artifact_id"] in artifacts, "initial_plan_not_before_c6")
    execution, lead = delivery_followups(dispatch, artifacts[dispatch["initial_analysis_artifact_id"]]["content_json"])
    if comparison["state"] == "eligible":
        rid = comparison["result_id"]
        old = context.prior_results[rid]
        require(old["validation_state"] == "accepted" and old["conclusion_state"] != "unavailable"
                and bool(old["conclusion"]), "frozen_comparison_not_usable")
        value = {key: old[key] for key in ("conclusion", "conclusion_state", "conclusion_origin", "validation_state", "delivery_state")}
        value["comparison_result_id"] = rid
        owners = sorted(set(context.alerts) & set(comparison["prior_scope"]["alert_ids"]))
        require(bool(owners), "frozen_comparison_scope_unavailable")
        lead.insert(0, {"original": value, "required": True,
            "entry": {"role": "prior_analysis", "alert_ids": owners, "value": value},
            "source": {"ref": reference("result", rid, "prior_analysis"), "alert_ids": owners}})
    bases = sorted([row for row in artifacts.values() if row["kind"] == "source_snapshot"
        and row["content_json"].get("type") in {"materials", "query_projection", "deep_summary", "graph_snapshot"}], key=lambda r: r["id"])
    materials = [row["content_json"] for row in bases if row["content_json"].get("type") == "materials"]
    require(len(materials) == 1, "frozen_material_catalog_unavailable_or_ambiguous")
    projections = sorted([row for row in bases if row["content_json"].get("type") == "query_projection"],
                         key=lambda row: (row["captured_at"], row["id"]))
    state, graphs = graph_candidates(bases, artifacts)
    prepared = case_followup_input.build("C6", context, copy.deepcopy(base), artifacts,
        previous=previous, prior_id=prior_id, material=materials[0], projections=projections,
        extra={"round": "final_delivery", "comparison": comparison, "followup_execution": execution, "graph_state": state,
            **({"preliminary_analysis": {"state": "unavailable", "reason": "no_accepted_main_analysis"}}
               if previous is None else {})},
        lead=lead, graphs=graphs)
    save(output / "prepared.json", prepared)
    require(prepared["ready"], "candidate_c6_input_unavailable")
    return request_body(policy, "C6", prepared["messages"], final_format(prepared, context, comparison))


def candidate_row(stage, receipt=None):
    # Admission input includes the meter's safety allowance and, when required
    # by the backend profile, the wire envelope. Do not substitute provider usage.
    return {"stage": stage, "measurement_state": "unavailable" if receipt is None else "measured",
        "input_tokens": receipt["context_input_tokens"] if receipt else None,
        "available_input_tokens": receipt["context_tokens"] - receipt["output_tokens"] if receipt else None,
        "fits": receipt["context_fits"] if receipt else None}


def tokenizer_transport(endpoint, output, *, inner=None):
    import httpx
    tokenizer_endpoint(endpoint)
    class TokenizerOnly(httpx.AsyncBaseTransport):
        def __init__(self):
            self.inner = inner if inner is not None else httpx.AsyncHTTPTransport(retries=0)
            self.calls = 0

        async def handle_async_request(self, request):
            require(request.method == "POST" and request.url == httpx.URL(endpoint), "non_tokenizer_request_rejected")
            require(self.calls < 2, "tokenizer_retry_rejected")
            value = json.loads(request.content)
            common = {"model", "add_special_tokens", "return_token_strs"}
            require(set(value) in (common | {"messages", "add_generation_prompt"}, common | {"prompt"}),
                    "non_tokenizer_payload_rejected")
            self.calls += 1
            save(output / f"tokenizer-request-{self.calls}.json", value)
            response = await self.inner.handle_async_request(request)
            await response.aread()
            save(output / f"tokenizer-response-{self.calls}.json", {
                "status_code": response.status_code, "body": response.text})
            return response

        async def aclose(self):
            await self.inner.aclose()
    return TokenizerOnly()


async def measure_batch(config, *, transport_factory=tokenizer_transport):
    from app.socai2.token_budget import BackendTokenMeter
    output = Path(config["output_dir"])
    save(output / "execution-claim.json", {"mode": config["mode"]})  # Exclusive: never rerun a finished attempt.
    results = [candidate_row(stage) for stage in config["stages"]]
    try:
        policy, meter_policy = configure(config)
        frozen = Frozen(config)
        context, base = base_input(frozen, policy, output)
        for index, stage in enumerate(config["stages"]):
            folder = output / stage
            folder.mkdir(mode=0o700)
            try:
                body = (c3_request if stage == "C3" else c6_request)(frozen, context, base, policy, folder)
                save(folder / "request.json", body)
                transport = transport_factory(config["tokenizer"]["endpoint"], folder)
                receipt = await BackendTokenMeter(meter_policy, transport=transport).measure(body, stage)
                save(folder / "measurement.json", receipt)
                results[index] = candidate_row(stage, receipt)
            except Exception:  # noqa: BLE001 -- diagnostic values must stay in private files
                save(folder / "exception.json", {"traceback": traceback.format_exc()})
    except Exception:  # noqa: BLE001 -- diagnostic values must stay in private files
        save(output / "exception.json", {"traceback": traceback.format_exc()})
    save(output / "candidate-redacted-report.json", results)
    save(output / "operation-status.json", {"mode": config["mode"], "status": "local_report_saved",
        "boundary": "no_generation_no_database_no_deployment_no_run_mutation",
        "statistics_release": "requires_user_redaction_confirmation"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    path = args.config.resolve()
    # Capture before importing application code; no request, exception or
    # derived measurement is ever emitted through the command's stdout/stderr.
    os.umask(0o077)
    try:
        fd = os.open(path.parent / "execution.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError:
        print(json.dumps({"status": "entry_not_started", "report_directory": str(path.parent)}))
        return 1
    saved = False
    previous_logging = logging.root.manager.disable
    with os.fdopen(fd, "w") as output, contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        logging.disable(logging.CRITICAL)
        try:
            config = load_config(path)
            asyncio.run(measure_batch(config))
            saved = True
        except Exception:  # noqa: BLE001 -- diagnostic values must stay in private files
            traceback.print_exc()
        finally:
            logging.disable(previous_logging)
    print(json.dumps({"status": "local_report_saved" if saved else "entry_not_completed",
                      "report_directory": str(path.parent)}))
    return 0 if saved else 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services/api"))
    raise SystemExit(main())
