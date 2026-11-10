"""Bounded runner checks with transport doubles; no model/network calls."""
import copy
import json

import pytest

from . import model_eval as evaluation
from .model_worker import visible_response


def test_visible_answer_and_usage_remain_exact_without_hidden_reasoning():
    raw = {"choices": [{"message": {"content": '{"analysis":"visible business answer"}',
            "reasoning_content": "private reasoning", "provider_specific_fields": {"reasoning": "private nested"}},
            "finish_reason": "stop"}], "usage": {"completion_tokens": 17}}
    before = copy.deepcopy(raw)
    visible, removed = visible_response(raw, {"reasoning_content", "reasoning", "analysis"})
    assert raw == before
    assert visible["choices"][0]["message"]["content"] == raw["choices"][0]["message"]["content"]
    assert visible["usage"] == raw["usage"] and len(removed) == 2
    assert "private" not in json.dumps([visible, removed])
    assert all(item["bytes"] > 0 and len(item["sha256"]) == 64 for item in removed)


@pytest.mark.parametrize("state,expected_calls", [("transport_unknown_no_retry", 1), ("response_received", 2)])
def test_one_attempt_per_arm_unknown_stops_and_ended_batch_cannot_redispatch(tmp_path, monkeypatch, state, expected_calls):
    config = {"expected_route": {"model": "test"}, "preflight_timeout_seconds": 30}
    plan = {"cells": [{"id": name, "body": {}} for name in ("before", "after")], "timeout_seconds": 300,
            "request_sha256": {"before-request.json": "before", "after-request.json": "after"}}
    preflight = {"state": "ready", "model": "test", "runtime_sha256": "unchanged"}
    evaluation.save(tmp_path / "preflight.json", preflight)
    evaluation.save(tmp_path / "plan-and-packets.json", plan)
    monkeypatch.setattr(evaluation, "validate_plan", lambda *_: plan)
    calls = []

    def fake_remote(_, task):
        if task["phase"] == "preflight":
            return preflight
        calls.append(task)
        return {"state": state}

    monkeypatch.setattr(evaluation, "remote", fake_remote)
    evaluation.run(config, tmp_path)
    assert len(calls) == expected_calls and len({c["cell"] for c in calls}) == expected_calls
    with pytest.raises(FileExistsError):
        evaluation.run(config, tmp_path)
    assert len(calls) == expected_calls


def test_frozen_input_tamper_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluation, "ROOT", tmp_path)
    source = tmp_path / "source.json"
    source.write_text("{}")
    evaluation.save(tmp_path / "plan-and-packets.json", {"config": {}, "source_sha256": {"source.json": evaluation.sha(source)},
        "request_sha256": {}, "cells": []})
    evaluation.validate_plan({}, tmp_path)
    source.write_text('{"changed":true}')
    with pytest.raises(AssertionError, match="prepared_source_changed"):
        evaluation.validate_plan({}, tmp_path)


def test_parseable_but_truncated_response_never_accepted():
    result = {"state": "response_received", "raw": {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]}}
    checked = evaluation.assess(result, {"id": "before"}, {}, {})
    assert checked["error"] == "incomplete_generation" and not checked["strict_accepted"]
    assert checked["partial"] is None and checked["usage"]["total_tokens"] is None


def test_unexpected_model_route_stops_before_generation():
    with pytest.raises(AssertionError, match="unexpected_model_route"):
        evaluation.check_route({"expected_route": {"model": "expected"}}, {"state": "ready", "model": "other"})
