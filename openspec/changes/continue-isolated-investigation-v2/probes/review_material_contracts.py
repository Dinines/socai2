"""Reproduce review I1/I2/I3 without clients, services or runtime changes.

Run from any directory with the project's Agents dependencies installed:
  python -B review_material_contracts.py [--output /path/to/receipt.json]

A successful exit means the reviewed baseline failures were reproduced. It
does not mean those failures were fixed or investigation quality was accepted.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[4]
BASELINE = "541511ce6965ec19b633c9ee550106695a29b06a"


def deny_network(*args, **kwargs):
    raise AssertionError("review probe must not open a network connection")


def run(runner: asyncio.Runner) -> dict:
    sys.path[:0] = [str(ROOT / "services/agents/tests"), str(ROOT / "services/agents")]
    from test_evidence_view_contract import EVENT, query, record, scope, view
    from test_analysis_adoption_contract import candidate
    from test_execution_models_contract import ATTEMPT, STEP, Model
    from test_execution_tools_contract import FakeStore
    from app.investigation_v2.analysis_adoption import adopt_candidate
    from app.investigation_v2.execution_models import DurableAnalysis, MAX_INPUT_BYTES, make_analysis_messages
    from app.investigation_v2.execution_state import ExecutionRejected
    from app.investigation_v2.execution_store import canonical_json
    from app.llm.contract_rules import LLMInputContract

    optional_body = []
    for name, message in (("short", "collector note"), ("long_513_ascii", "x" * 513),
                          ("structured", {"note": "collector note"})):
        try:
            evidence = view(query([record(message)]))
            result = {"case": name, "result": "view_ok", "events": len(evidence.model_view["events"])}
        except ValueError as exc:
            result = {"case": name, "result": type(exc).__name__, "reason": str(exc)}
        optional_body.append(result)
    assert optional_body[0]["result"] == "view_ok"
    assert optional_body[1]["reason"] == "data_only_excerpt_exceeds_byte_limit"
    assert optional_body[2]["reason"] == "source_message_must_be_text"

    rows = [record("collector note A"), record("collector note B")]
    versions = sorted(row["content_hash"] for row in rows)
    for row in rows:
        row.update(identity_state="conflict", conflict_version_hashes=versions)
    conflicting = view(query(rows))
    result = adopt_candidate(scope(), conflicting, candidate(conflicting, "focused_analysis"),
                             mode="focused_analysis", current_snapshot_ref=conflicting.snapshot_ref)
    conflict = {
        "same_visible_fields": conflicting.model_view["events"][0]["fields"] == conflicting.model_view["events"][1]["fields"],
        "delivered_versions": len(conflicting.model_view["events"]),
        "adoption_status": result["status"],
        "accepted_questions": [answer["question"] for answer in result["answers"]],
        "rejection_reasons": [rejection["reason"] for rejection in result["rejections"]],
    }
    assert conflict["same_visible_fields"]
    assert "answer_ignores_source_conflict" in conflict["rejection_reasons"]
    assert conflict["accepted_questions"] == ["Q2", "Q5"]

    sizes = []
    last_view = None
    for count in range(1, 11):
        records = [record("x" * 128, event_id=EVENT if i == 0 else uuid5(NAMESPACE_URL, f"review-budget:{i}"))
                   for i in range(count)]
        last_view = view(query(records))
        messages = LLMInputContract.validate(make_analysis_messages(last_view, "focused_analysis"))
        body = canonical_json(messages)
        rejected = False
        try:
            canonical_json(messages, max_bytes=MAX_INPUT_BYTES)
        except ExecutionRejected:
            rejected = True
        sizes.append({"records": count, "view_bytes": len(canonical_json(last_view.model_view).encode("utf-8")),
                      "messages_bytes": len(body.encode("utf-8")), "limit_bytes": MAX_INPUT_BYTES,
                      "request_rejected": rejected})
    assert not sizes[0]["request_rejected"]
    assert sizes[-1]["view_bytes"] < MAX_INPUT_BYTES < sizes[-1]["messages_bytes"]

    async def blocked_execution():
        store = FakeStore()
        model = Model(store, "{}")
        result = await DurableAnalysis(store, scope(), model).execute(
            last_view, "focused_analysis", step_id=STEP, attempt_id=ATTEMPT,
            subtask_id="review-budget-probe", current_snapshot_ref=last_view.snapshot_ref)
        observed = {"execution_status": result["execution_status"], "reason": result.get("reason"),
                    "dispatch_started": result["dispatch_started"], "fake_model_calls": len(model.calls),
                    "fake_reservations": len(store.reserves), "fake_completions": len(store.completions)}
        assert observed == {"execution_status": "blocked", "reason": "analysis_ExecutionRejected",
                            "dispatch_started": False, "fake_model_calls": 0,
                            "fake_reservations": 0, "fake_completions": 0}
        return observed

    blocked = runner.run(blocked_execution())
    paths = ["services/agents/app/investigation_v2/" + name + ".py" for name in
             ("evidence_view", "analysis_adoption", "execution_models", "execution_store", "question_deep")]
    paths += ["services/agents/tests/" + name + ".py" for name in
              ("test_evidence_view_contract", "test_analysis_adoption_contract",
               "test_execution_models_contract", "test_execution_tools_contract")]
    return {"schema": "investigation_review_reproduction.v1", "reviewed_git_baseline": BASELINE,
            "python": sys.version, "mode": "offline_in_memory_with_fake_store_and_model",
            "network_guard": "socket.connect/connect_ex/create_connection rejected during imports and execution",
            "conclusion": "baseline_findings_reproduced_not_fixed",
            "I1_optional_body": optional_body, "I2_request_sizes": sizes,
            "I2_actual_executor": blocked, "I3_body_only_versions": conflict,
            "source_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths},
            "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "limitations": ["No real HTTP, PG, CH, Kafka or model calls; no business writes or deployment",
                            "Byte sizes describe normalized messages, not a provider HTTP envelope or token count",
                            "No model-value comparison or general quality acceptance"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    # Windows asyncio opens an internal loopback socketpair for its wakeup
    # channel. Initialize/close that channel outside the probe network guard.
    with asyncio.Runner() as runner:
        with patch.object(socket.socket, "connect", deny_network), patch.object(socket.socket, "connect_ex", deny_network), \
                patch.object(socket, "create_connection", deny_network):
            report = run(runner)
    body = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(body, encoding="utf-8")
    print(body, end="")
