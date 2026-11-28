"""Prepared only: exact-scope, read-only stage_delivery metadata projection.

No model calls, full artifacts, response/input values, business mutations, or
automatic retries. Run only after the coordinator obtains the exact read scope.
"""

import argparse
import contextlib
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

HIDDEN_CODE = "unrecognized_program_code_hidden"
HIDDEN_PATH = "$.[non_contract_path_hidden]"
PARSE_STATES = ("complete_json", "closed_units", "unusable", "no_response")
FINISH_REASONS = ("stop", "length", "incomplete", "content_filter", "tool_calls", "function_call")
REASON_CODES = (
    "no_content", "json_incomplete", "json_syntax_invalid", "json_number_invalid",
    "json_string_surrogate_invalid", "json_scalar_boundary_invalid", "duplicate_json_key",
    "json_trailing_content", "container_type_invalid", "unknown_section", "section_not_complete",
    "provider_length", "unit_content_blocked", "required_array_empty",
    "incident_answer_scope_invalid", "section_item_limit_exceeded", "duplicate_members_definition",
    "unit_shape_or_identity_invalid", "members_coverage_incomplete", "severity_opinion_content_blocked",
    "model_choices_invalid", "model_response_not_complete", "model_content_or_tool_protocol_invalid",
    "model_usage_unknown_or_inconsistent", "provider_usage_exceeds_reservation",
    "stage_core_conclusion_unavailable", "alert_answer_shape_invalid", "alert_answer_guard",
    "alert_answer_duplicate_key", "alert_answer_nonfinite",
)


def contract_paths():
    """Static A/I contract positions only; never derive names from records."""
    paths = {"$", "$.diagnosis", "$.severity_opinion", "$.business_verdict"}
    scalar_fields = ("verdict", "confidence", "rationale")
    paths.update("$." + key for key in scalar_fields)
    for key in ("summary", "conclusion", "source_ids", "limitations"):
        path = "$.diagnosis." + key
        paths.add(path)
        if key in {"source_ids", "limitations"}:
            paths.add(path + "[*]")
    paths.update(("$.evidence_ids", "$.evidence_ids[*]"))
    items = {
        "members": ("alert_ref", "state", "assessment", "source_ids", "limitations"),
        "findings": ("statement", "state", "alert_refs", "source_ids", "limitations"),
        "open_questions": ("text", "alert_refs", "source_ids", "evidence_requirements"),
        "recommendations": ("reason", "source_ids"),
        "attck_mappings": ("tactic_id", "technique_id", "evidence_ids"),
    }
    lists = {"source_ids", "evidence_ids", "alert_refs", "limitations", "evidence_requirements"}
    for key, fields in items.items():
        base = "$." + key
        paths.update((base, base + "[*]"))
        for field in fields:
            path = base + "[*]." + field
            paths.add(path)
            if field in lists:
                paths.add(path + "[*]")
    for key in ("level", "reason", "impact_basis", "source_refs", "limitations"):
        path = "$.severity_opinion." + key
        paths.add(path)
        if key in {"source_refs", "limitations"}:
            paths.add(path + "[*]")
    for key in ("confirmed", "potential"):
        path = "$.severity_opinion.impact_basis." + key
        paths.update((path, path + "[*]"))
    return sorted(paths)


def load(path):
    return json.loads(Path(path).read_bytes())


def checked_bytes(path, expected_sha256):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("reviewed_file_changed")
    return raw


def save(path, value):
    with path.open("x") as stream:
        os.chmod(path, 0o600)
        json.dump(value, stream, ensure_ascii=False, indent=2)


def collect(cfg, out):
    expected_keys = {"connection_config_file", "connection_config_sha256", "transport_sha256",
                     "scope_file", "scope_sha256", "query_sha256", "output_dir"}
    if set(cfg) != expected_keys:
        raise ValueError("metadata_config_invalid")
    connection = json.loads(checked_bytes(cfg["connection_config_file"], cfg["connection_config_sha256"]))
    scope = json.loads(checked_bytes(cfg["scope_file"], cfg["scope_sha256"]))
    if set(scope) != {"tenant_id", "run_ids", "stages"} or scope["tenant_id"] != connection["tenant_id"]:
        raise ValueError("metadata_scope_invalid")
    UUID(scope["tenant_id"])
    if (not isinstance(scope["run_ids"], list) or not scope["run_ids"]
            or len(set(scope["run_ids"])) != len(scope["run_ids"])):
        raise ValueError("metadata_run_scope_invalid")
    for identity in scope["run_ids"]:
        UUID(identity)
    if (not isinstance(scope["stages"], list) or not scope["stages"]
            or not set(scope["stages"]) <= {"A", "I"}
            or len(set(scope["stages"])) != len(scope["stages"])):
        raise ValueError("metadata_stage_scope_invalid")
    query = checked_bytes(Path(__file__).with_name("receive_metadata.sql"), cfg["query_sha256"]).decode()
    checked_bytes(connection["transport_source"], cfg["transport_sha256"])
    spec = importlib.util.spec_from_file_location("reviewed_receive_metadata_transport", connection["transport_source"])
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    channel = copy.deepcopy(connection["maintenance"])
    channel["stderr_file"] = str(out / "transport-private.log")
    db = transport.MaintenancePsql(channel, connection["database"])
    try:
        db.connect()
        db.begin()  # The frozen adapter begins REPEATABLE READ READ ONLY.
        db.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": scope["tenant_id"]})
        binding = db.execute(text("SELECT current_database() AS database,current_user AS role,"
            "current_setting('transaction_read_only') AS readonly")).one()
        if binding != {"database": connection["database"], "role": channel["expected_user"], "readonly": "on"}:
            raise ValueError("metadata_connection_binding_invalid")
        params = {**scope, "contract_paths": contract_paths(), "reason_codes": list(REASON_CODES),
                  "parse_states": list(PARSE_STATES), "finish_reasons": list(FINISH_REASONS),
                  "hidden_code": HIDDEN_CODE, "hidden_path": HIDDEN_PATH}
        rows = db.execute(text(query), params).all()
        diagnostics = []
        for row in rows:
            if set(row) != {"diagnostic"}:
                raise ValueError("metadata_projection_invalid")
            diagnostics.append(row["diagnostic"])
        db.rollback()
        save(out / "receive-metadata.private.json", {"diagnostics": diagnostics})
    finally:
        try:
            db.rollback()
        finally:
            db.dispose()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    # Never include configuration, scope, exception text, or data in console output.
    status, private_path = "receive_metadata_not_completed", None
    try:
        cfg = load(args.config)
        out = Path(cfg["output_dir"]).resolve()
        private_root = (Path(__file__).resolve().parents[4] / ".local" / "validation").resolve()
        if not out.is_relative_to(private_root) or out == private_root:
            raise ValueError("private_output_directory_required")
        out.mkdir(mode=0o700, exist_ok=False)
        private_path = str(out)
        with ((out / "operation-private.log").open("x") as log,
              contextlib.redirect_stdout(log), contextlib.redirect_stderr(log)):
            try:
                collect(cfg, out)
                status = "receive_metadata_report_saved"
            except BaseException:  # noqa: BLE001 - Never leak transport/data exceptions.
                log.write("receive_metadata_operation_not_completed\n")
        save(out / "operation-status.json", {"status": status})
    except BaseException:  # noqa: BLE001 - The console is status-only, including setup errors.
        status = "receive_metadata_not_completed"
    print(json.dumps({"status": status, "private_path": private_path}))


if __name__ == "__main__":
    main()
