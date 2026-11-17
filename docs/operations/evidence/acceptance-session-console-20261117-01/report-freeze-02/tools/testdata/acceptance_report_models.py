"""Project saved model messages and visible answers; never invoke a model."""
from __future__ import annotations

from collections import Counter

from alert_scenarios import json_bytes


def obj(value):
    return value if isinstance(value, dict) else {}


def counter(value):
    return value if type(value) is int and value >= 0 else None


def model_report(artifacts, origins, complete):
    requests = [a for a in artifacts.values() if a.get("kind") == "model_request"]
    responses = {}
    for artifact in artifacts.values():
        content = obj(artifact.get("content_json"))
        if artifact.get("kind") == "source_snapshot" and isinstance(content.get("request_artifact_id"), str) and content["request_artifact_id"] in artifacts and "raw" in content:
            responses.setdefault(content["request_artifact_id"], []).append(artifact)
    items, files, issues = [], {}, []
    for request in sorted(requests, key=lambda a: (str(a.get("created_at", "")), a["id"])):
        identity = request["id"]
        content = obj(request.get("content_json"))
        body = obj(obj(content.get("payload")).get("body") if "payload" in content else content.get("body"))
        prefix = "models/" + identity + "/"
        item = {"request_artifact_id": identity, "run_id": request.get("run_id"),
                "step_id": request.get("step_id"), "source": origins[identity], "exports": {},
                "finish_reason": None, "usage": {k: None for k in ("prompt_tokens", "completion_tokens", "total_tokens")},
                "cost": None, "cost_state": "unknown"}

        def problem(code, identity=identity):
            issues.append({"code": code, "request_artifact_id": identity, "source": origins[identity]})

        messages = body.get("messages")
        if isinstance(messages, list) and messages and all(isinstance(m, dict)
                and m.get("role") in {"system", "developer", "user", "assistant", "tool"}
                and isinstance(m.get("content"), str) for m in messages):
            # Deliberately exclude HTTP headers, hidden reasoning and provider internals.
            files[prefix + "messages.json"] = json_bytes([{k: m[k] for k in ("role", "content")} for m in messages])
            item["exports"]["messages"] = prefix + "messages.json"
        else:
            problem("model_messages_unreadable")
        schema = body.get("response_format")
        if isinstance(schema, dict):
            files[prefix + "schema.json"] = json_bytes(schema)
            item["exports"]["schema"] = prefix + "schema.json"
        else:
            item["schema_state"] = "not_recorded"
        candidates = responses.get(identity, [])
        if len(candidates) != 1:
            problem("model_original_missing" if not candidates else "model_original_ambiguous")
        else:
            response = candidates[0]
            raw = obj(obj(response.get("content_json")).get("raw"))
            item["response_artifact_id"] = response["id"]
            item["response_source"] = origins[response["id"]]
            usage = obj(raw.get("usage"))
            item["usage"] = {k: counter(usage.get(k)) for k in item["usage"]}
            choices = raw.get("choices")
            if isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict):
                choice = choices[0]
                text = obj(choice.get("message")).get("content")
                if isinstance(text, str):
                    files[prefix + "output.txt"] = text.encode("utf-8")
                    item["exports"]["output"] = prefix + "output.txt"
                    item["finish_reason"] = choice.get("finish_reason") if isinstance(choice.get("finish_reason"), str) and choice["finish_reason"] in {
                        "stop", "length", "tool_calls", "content_filter", "function_call"} else None
                else:
                    problem("model_visible_output_unreadable")
            else:
                problem("model_choices_unreadable")
        items.append(item)
    subtotal = {k: sum(r["usage"][k] or 0 for r in items) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
    unknown = {k: sum(r["usage"][k] is None for r in items) for k in subtotal}
    summary = {"saved_request_count": len(items), "request_count": len(items) if complete else None,
               "coverage": "saved_snapshots" if complete else "incomplete",
               "usage": {k: subtotal[k] if complete and not unknown[k] else None for k in subtotal},
               "known_usage_subtotal": subtotal, "unknown_usage_requests": unknown,
               "cost": None, "cost_state": "unknown", "requests": items,
               "finish_reasons": dict(Counter(r["finish_reason"] or "unknown" for r in items)),
               "issues": issues, "new_calls_by_report": 0}
    return summary, files
