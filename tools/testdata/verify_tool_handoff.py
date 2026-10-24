#!/usr/bin/env python3
"""Offline agents_probe trace reconciliation, never semantic or backend scoring.

The original probe executes tool calls serially but its execution receipts have
no call_id. We only pair complete, ordered signature occurrences within the same
tenant/Run/Alert. Missing repeated occurrences or contradictory order stay
unverified. Hashes show consistency of the supplied files, not authenticity.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
LOCAL_ROOT = ROOT / ".local"
RENDERER = ROOT / "services/agents/app/prompting/tool_results.py"
SCHEMA = "socai2-tool-handoff-check/v1"
KINDS = ("model-request", "model-response", "tool-request", "tool-result")


def digest(value) -> str:
    data = value if isinstance(value, bytes) else json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(data).hexdigest()


def renderer():
    """Reuse the original stdlib-only renderer; do not import the service app."""
    name = "_testdata_handoff_renderer"
    spec = importlib.util.spec_from_file_location(name, RENDERER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolves the module during import.
    spec.loader.exec_module(module)
    return module.render_tool_message


def identity(row) -> tuple[str, str, str]:
    alert = row.get("alert")
    if not isinstance(alert, dict):
        raise ValueError("receipt lacks explicit tenant/Run/Alert identity")
    try:
        return tuple(str(UUID(alert[key])) for key in ("tenant_id", "run_id", "canonical_alert_id"))
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ValueError("receipt has invalid tenant/Run/Alert identity") from exc


def signature(name, args) -> str:
    if not isinstance(name, str) or not name or not isinstance(args, dict):
        raise ValueError("tool name and object arguments required")
    return digest({"tool": name, "args": args})


def call_fields(call):
    if not isinstance(call, dict) or call.get("type") != "function":
        raise ValueError("unsupported model tool call")
    function = call.get("function") or {}
    args = function.get("arguments")
    if isinstance(args, str):
        args = json.loads(args)
    call_id = call.get("id")
    if not isinstance(call_id, str) or not call_id:
        raise ValueError("model tool call lacks identity")
    return call_id, signature(function.get("name"), args)


def load_trace(directory: Path):
    directory = directory.resolve(strict=True)
    records, refs = {}, {}
    for kind in KINDS:
        records[kind] = {}
        paths = sorted(directory.glob(f"{kind}-*.json"))
        if len(paths) > 2000:
            raise ValueError("trace exceeds bounded file count")
        for path in paths:
            match = re.fullmatch(rf"{kind}-(\d+)\.json", path.name)
            if not match or path.is_symlink() or path.stat().st_size > 16 * 1024 * 1024:
                raise ValueError("invalid or oversized trace file")
            index = int(match[1])
            raw = path.read_bytes()
            row = json.loads(raw)
            if not isinstance(row, dict) or type(row.get("index")) is not int or row["index"] != index or index < 1:
                raise ValueError("trace index differs from filename")
            if index in records[kind]:
                raise ValueError("duplicate trace index")
            records[kind][index] = row
            refs[kind, index] = {"file": path.name, "sha256": digest(raw)}
    if not any(records.values()):
        raise ValueError("no probe trace files found")
    return records, refs


def return_status(row):
    if "interrupted_by" in row:
        return "interrupted"
    if "result" not in row:
        return "missing_return"
    value = row["result"]
    if isinstance(value, dict):
        if value.get("error"):
            return "error"
        if value.get("available") is False:
            return "unavailable"
        if value.get("available") is True:
            return "available"
    return "returned_unclassified"


def verify(directory: Path) -> dict:
    records, refs = load_trace(directory)
    requests, responses = records["model-request"], records["model-response"]
    executions, returns = records["tool-request"], records["tool-result"]
    render = renderer()
    calls, issues = [], []
    scopes = {index: identity(row) for index, row in requests.items()}
    for index, response in sorted(responses.items()):
        if index not in requests:
            issues.append({"code": "response_without_request", "reference": refs["model-response", index]})
            continue
        choices = (response.get("body") or {}).get("choices", [])
        for choice in choices:
            for position, call in enumerate((choice.get("message") or {}).get("tool_calls") or []):
                call_id, sig = call_fields(call)
                calls.append({"scope": scopes[index], "request_index": index, "position": position,
                              "call_id": call_id, "signature": sig,
                              "reason": "ambiguous_response_choices" if len(choices) != 1 else
                                        ("response_not_successful" if response.get("status_code") != 200 else None)})
    id_counts = Counter((call["scope"], call["call_id"]) for call in calls)
    for call in calls:
        if id_counts[call["scope"], call["call_id"]] != 1:
            call["reason"] = "duplicate_call_id_in_run"

    call_groups, execution_groups = defaultdict(list), defaultdict(list)
    for call in calls:
        call_groups[call["scope"], call["signature"]].append(call)
    for index, execution in sorted(executions.items()):
        execution_groups[identity(execution), signature(execution.get("tool"), execution.get("args"))].append(index)
    matches, reasons = {}, {}
    for key, indexes in execution_groups.items():
        candidates = call_groups.get(key, [])
        if len(candidates) != len(indexes):
            for index in indexes:
                reasons[index] = "ambiguous_or_missing_signature_occurrence"
        else:
            for index, call in zip(indexes, candidates, strict=True):
                if call["reason"]:
                    reasons[index] = call["reason"]
                else:
                    matches[index] = call
    # Probe execution is serial. Signature matching may not silently reorder it.
    by_scope = defaultdict(list)
    for index, call in sorted(matches.items()):
        by_scope[call["scope"]].append((index, call))
    for ordered in by_scope.values():
        positions = [(call["request_index"], call["position"]) for _, call in ordered]
        if positions != sorted(positions):
            for index, _ in ordered:
                matches.pop(index)
                reasons[index] = "execution_order_conflicts_with_model_calls"

    output = []
    for index, execution in sorted(executions.items()):
        scope = identity(execution)
        row = {"execution_index": index, "tenant_id": scope[0], "run_id": scope[1],
               "alert_id": scope[2], "tool": execution["tool"], "args_sha256": digest(execution["args"]),
               "invocation": "recorded", "return_status": "missing_return", "pairing": "unverified",
               "handoff": "unverified", "references": {"tool_request": refs["tool-request", index]}}
        returned = returns.get(index)
        integrity = True
        if returned is not None:
            row["references"]["tool_result"] = refs["tool-result", index]
            integrity = identity(returned) == scope and signature(returned.get("tool"), returned.get("args")) == signature(execution["tool"], execution["args"])
            if not integrity:
                row["reason"] = "execution_return_identity_or_arguments_differ"
                row["return_status"] = "unverified"
            else:
                row["return_status"] = return_status(returned)
                if "result" in returned:
                    row["result_sha256"] = digest(returned["result"])
                    expected_content = render(returned["result"])
                    row["rendered_sha256"] = digest(expected_content.encode())
                    integrity = returned.get("model_tool_content") == expected_content
                    row["render_consistency"] = "verified" if integrity else "mismatch"
                    if not integrity:
                        row["return_status"] = "unverified"
                        row["reason"] = "recorded_render_differs_from_original_renderer"
        call = matches.get(index)
        if call is None:
            row.setdefault("reason", reasons[index])
        else:
            row.update({"pairing": "ordered_signature", "call_id": call["call_id"],
                        "origin_request_index": call["request_index"]})
            row["references"].update({"model_request": refs["model-request", call["request_index"]],
                                       "model_response": refs["model-response", call["request_index"]]})
            if integrity and returned is not None and "result" in returned:
                row["handoff"] = "not_in_later_request"
                for later, request in sorted(requests.items()):
                    if later <= call["request_index"] or scopes[later] != scope:
                        continue
                    messages = (request.get("body") or {}).get("messages", [])
                    hits = [(pos, message) for pos, message in enumerate(messages)
                            if message.get("role") == "tool" and message.get("tool_call_id") == call["call_id"]]
                    if not hits:
                        continue
                    row["later_request_index"] = later
                    row["references"]["later_request"] = refs["model-request", later]
                    if len(hits) != 1:
                        row.update(handoff="unverified", reason="duplicate_tool_messages")
                        break
                    pos, message = hits[0]
                    prior = [candidate for earlier in messages[:pos] if earlier.get("role") == "assistant"
                             for candidate in earlier.get("tool_calls") or [] if candidate.get("id") == call["call_id"]]
                    if len(prior) != 1 or call_fields(prior[0]) != (call["call_id"], call["signature"]):
                        row.update(handoff="unverified", reason="preceding_assistant_call_differs_or_missing")
                    elif message.get("content") != returned["model_tool_content"]:
                        row.update(handoff="content_mismatch", reason="tool_message_differs_from_recorded_render")
                    else:
                        row["handoff"] = "verified_in_later_request"
                    break
        output.append(row)

    paired = {(call["scope"], call["call_id"]) for call in matches.values()}
    unpaired = [{"tenant_id": call["scope"][0], "run_id": call["scope"][1], "alert_id": call["scope"][2],
                 "call_id": call["call_id"], "request_index": call["request_index"],
                 "status": call["reason"] or "no_unique_execution_pair"}
                for call in calls if (call["scope"], call["call_id"]) not in paired]
    orphans = [refs["tool-result", index] for index in sorted(returns) if index not in executions]
    return {"schema_version": SCHEMA, "source_directory": str(directory.resolve()),
            "renderer": {"file": str(RENDERER.relative_to(ROOT)), "sha256": digest(RENDERER.read_bytes())},
            "counts": {"recorded_invocations": len(output), "model_tool_calls": len(calls),
                       "return_status": dict(Counter(row["return_status"] for row in output)),
                       "handoff": dict(Counter(row["handoff"] for row in output)),
                       "unpaired_model_calls": len(unpaired), "orphan_returns": len(orphans)},
            "records": output, "unpaired_model_calls": unpaired, "orphan_returns": orphans, "issues": issues,
            "limits": ["offline_consistency_of_supplied_files_not_authenticity",
                       "serial_probe_order_used_because_execution_receipts_lack_call_id",
                       "recorded_invocation_does_not_prove_backend_query_or_relevant_evidence",
                       "missing_return_does_not_prove_the_invocation_completed_or_ran",
                       "available_does_not_prove_valid_evidence_or_source_coverage",
                       "render_comparison_uses_the_reported_current_renderer_hash",
                       "later_request_presence_does_not_prove_semantic_adoption",
                       "not_in_later_request_means_not_observed_in_supplied_trace"]}


def save_report(path: Path, report: dict) -> None:
    path = path.resolve()
    if not path.is_relative_to(LOCAL_ROOT.resolve()) or path == LOCAL_ROOT.resolve():
        raise ValueError("output must be a file under this checkout's .local")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    report = verify(args.trace)
    save_report(args.out, report)
    print(json.dumps({"output": str(args.out.resolve()), "counts": report["counts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
